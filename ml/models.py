import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_squared_error, precision_score, recall_score, f1_score, confusion_matrix
from xgboost import XGBRegressor, XGBClassifier

SENSORS = [2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]

FEATURES = [f"s{i}_sm" for i in SENSORS] + ["setting_1", "setting_2", "setting_3", "cycle"]


def nasa_score(y, pred):

    diff = np.asarray(pred) - np.asarray(y)

    terms = np.where(diff < 0,
                    np.exp(np.clip(-diff / 13, 0, 30)) - 1,
                    np.exp(np.clip(diff / 10, 0, 30)) - 1
                    )
    
    return float(terms.sum())


def make_regressor(kind):
    if kind == "LinearRegression":

        return make_pipeline(
            StandardScaler(), 
            LinearRegression()
            )
    
    return XGBRegressor(
                    n_estimators=250, 
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.85, 
                    colsample_bytree=0.85,
                    objective="reg:squarederror", 
                    random_state=42, n_jobs=4
                    )


def make_classifier(kind, positive_weight):
    if kind == "LogisticRegression":

        return make_pipeline(
            StandardScaler(), 
            LogisticRegression(
                            max_iter=1000,
                            class_weight="balanced", 
                            random_state=42
                            )
                        )
    
    return XGBClassifier(
        n_estimators=250, 
        max_depth=4, 
        learning_rate=0.05,
        subsample=0.85, 
        colsample_bytree=0.85,
        objective="binary:logistic", eval_metric="logloss",
        scale_pos_weight=positive_weight, random_state=42, n_jobs=4
        )


def evaluate_cv(train):
    """Engine-grouped cross validation; no engine appears in both folds"""

    x = train[FEATURES]

    y_reg = train["rul_capped"].values

    y_cls = (train["rul"] <= 30).astype(int).values

    groups = train["engine_uid"].values

    splits = list(GroupKFold(n_splits=5).split(x, y_reg, groups))

    positive_weight = max(1,
                        int((y_cls == 0).sum() / max(1, (y_cls == 1).sum()))
                        )

    metrics = []

    for kind in ["LinearRegression", "XGBoost"]:

        rmses, recalls, f1s = [], [], []

        for a, b in splits:

            reg = make_regressor(kind)

            reg.fit(x.iloc[a], y_reg[a])

            #because we don't want negatuve rul values, so if a value is negative it will be replaced by 0
            pred = np.maximum( 
                0, 
                reg.predict(x.iloc[b])
                )

            rmses.append(float(np.sqrt(mean_squared_error(y_reg[b], pred))))

            cls_kind = "LogisticRegression" if kind == "LinearRegression" else "XGBoost"

            cls = make_classifier(cls_kind, positive_weight)

            cls.fit(x.iloc[a], y_cls[a])

            predicted = (cls.predict_proba(x.iloc[b])[:, 1] >= 0.5).astype(int) #predict probablity of each class and convert them into int

            recalls.append(recall_score(y_cls[b], predicted, zero_division=0))

            f1s.append(f1_score(y_cls[b], predicted, zero_division=0))

        metrics += [
            (kind, "cv_rmse_capped", float(np.mean(rmses))),
            (kind, "cv_recall", float(np.mean(recalls))),
            (kind, "cv_f1", float(np.mean(f1s)))
            ]
    return metrics


def train_and_predict(cycles):

    train = cycles[cycles["split"] == "train"].copy()

    test = cycles[cycles["split"] == "test"].sort_values("cycle").groupby("engine_uid").tail(1).copy()

    if train.engine_uid.nunique() != 100 or test.engine_uid.nunique() != 100:
        raise ValueError("Expected 100 training engines and 100 test engines")
    
    if cycles[FEATURES + ["rul", "rul_capped"]].isna().any().any():
        raise ValueError("Silver contains missing ML features or RUL labels")
    
    metrics = evaluate_cv(train)

    x_train = train[FEATURES]

    x_test = test[FEATURES]

    y_reg = train["rul_capped"].values

    y_cls = (train["rul"] <= 30).astype(int).values

    positive_weight = max(1, int((y_cls == 0).sum() / max(1, (y_cls == 1).sum())))

    predictions = []

    for kind, cls_kind in [("LinearRegression", "LogisticRegression"), ("XGBoost", "XGBoost")]:

        reg = make_regressor(kind)

        reg.fit(x_train, y_reg)

        predicted_rul = np.maximum(0, reg.predict(x_test))

        cls = make_classifier(cls_kind, positive_weight)

        cls.fit(x_train, y_cls)

        probabilities = cls.predict_proba(x_test)[:, 1]

        for uid, rul, prob in zip(test.engine_uid, predicted_rul, probabilities):
            predictions.append({"engine_uid": int(uid), "model_name": kind,
                                "predicted_rul": float(rul), "failure_prob_30": float(prob)})

            
        # The held-out test truth is used ONLY to evaluate predictions, not as a model input.
        actual = test.rul.to_numpy()

        metrics.extend([(kind, "test_rmse_true", float(np.sqrt(mean_squared_error(actual, predicted_rul)))),
                        (kind, "test_nasa_score", nasa_score(actual, predicted_rul))])
        
        actual_cls = (actual <= 30).astype(int)

        decision = (probabilities >= 0.5).astype(int)

        tn, fp, fn, tp = confusion_matrix(actual_cls, decision, labels=[0, 1]).ravel()

        metrics.extend([(kind, "test_precision", precision_score(actual_cls, decision, zero_division=0)),
                        (kind, "test_recall", recall_score(actual_cls, decision, zero_division=0)),
                        (kind, "test_f1", f1_score(actual_cls, decision, zero_division=0)),
                        (kind, "tn", float(tn)), (kind, "fp", float(fp)),
                        (kind, "fn", float(fn)), (kind, "tp", float(tp))])
        
    return test, pd.DataFrame(predictions), metrics, train


def health_scores(train, test, preds):
    # Fit healthy reference ONLY on the first 20% of cycles of training engines

    maxcycles = train.groupby("engine_uid")["cycle"].transform("max")

    healthy = train[train.cycle <= np.maximum(1, np.ceil(maxcycles * 0.20))]

    columns = [f"s{i}_sm" for i in SENSORS]

    scaler = StandardScaler().fit(healthy[columns])

    forest = IsolationForest(n_estimators=200, contamination=0.08, random_state=42, n_jobs=4)

    forest.fit(scaler.transform(healthy[columns]))

    healthy_anomaly = -forest.score_samples(scaler.transform(healthy[columns]))

    test_anomaly = -forest.score_samples(scaler.transform(test[columns]))

    lo, hi = np.percentile(healthy_anomaly, [5, 95])
    if hi <= lo:
        hi = lo + 1e-6
    health = np.clip(100 * (hi - test_anomaly) / (hi - lo), 0, 100)

    main = preds[preds.model_name == "XGBoost"].copy().set_index("engine_uid")

    df = test[["engine_uid", "engine_id", "cycle", "cycle_date", "s4_sm", "s11_sm"]].copy()

    df["health_index"] = health

    df["predicted_rul"] = df.engine_uid.map(main.predicted_rul)

    df["failure_prob_30"] = df.engine_uid.map(main.failure_prob_30)

    if df[["predicted_rul", "failure_prob_30"]].isna().any().any():
        raise ValueError("Test engine missing an XGBoost prediction")
    
    cluster_data = StandardScaler().fit_transform(df[["health_index", "predicted_rul"]])

    km = KMeans(n_clusters=3, random_state=42, n_init=10).fit(cluster_data)

    avg_health = pd.DataFrame({"cluster": km.labels_, "health": health}).groupby("cluster").health.mean().sort_values()

    names = {int(k): label for k, label in zip(avg_health.index, ["Critical", "Degrading", "Healthy"])}

    df["degradation_stage"] = [names[int(c)] for c in km.labels_]
    
    # Baselines for expert rule R5, derived only from early train cycles.
    baselines = {}
    for col in ["s4_sm", "s11_sm"]:
        baselines[col] = (float(healthy[col].mean()), float(healthy[col].std()))
    return df, baselines
