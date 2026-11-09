"""Optional explanatory plot. Reads Silver only; does not change SQL Server."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import shap
from sqlalchemy import text
from config import connect
from models import FEATURES, make_regressor

engine = connect()
with engine.connect() as conn:
    cycles = pd.read_sql(text("SELECT * FROM silver.engine_cycles"), conn)
train = cycles[cycles.split == 'train']
test = cycles[cycles.split == 'test'].sort_values('cycle').groupby('engine_uid').tail(1)
if train.empty or test.empty:
    raise ValueError('Silver train or test data is missing')
model = make_regressor('XGBoost')
model.fit(train[FEATURES], train.rul_capped)
explainer = shap.TreeExplainer(model)
values = explainer(test[FEATURES])
shap.summary_plot(values.values, test[FEATURES], show=False, max_display=18)
out = Path(__file__).resolve().parent.parent / 'docs' / 'gold_results'
out.mkdir(parents=True, exist_ok=True)
plt.tight_layout()
plt.savefig(out / 'shap_summary.png', dpi=170, bbox_inches='tight')
plt.close()
print('Saved:', out / 'shap_summary.png')
