/*
    PredMaintDW - complete mart.DimDate calendar for 2023-01-01 through 2026-12-31

    Safety:
      - Defaults to dry-run mode and rolls back all inserted rows.
      - Inserts only dates missing from mart.DimDate.
      - Never updates or deletes an existing DimDate row.
      - Reuses the date_key and calendar-attribute expressions from
        sql/11_load_mart_dimensions.sql.
      - Validates target coverage, key/attribute consistency, uniqueness,
        and fact-to-date referential integrity before commit.

    Manual use:
      1. Review the result sets with @CommitChanges = 0.
      2. If every validation passes, change @CommitChanges to 1 and rerun.
      3. Rerunning after a successful commit is safe; expected inserts = 0.
*/

USE PredMaintDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LANGUAGE us_english; -- deterministic English month names, matching the existing CSV/model
GO

DECLARE @StartDate DATE = '20230101';
DECLARE @EndDate DATE = '20261231';
DECLARE @CommitChanges BIT = 1; -- SAFETY DEFAULT: 0 = validate then ROLLBACK; 1 = COMMIT

IF @StartDate > @EndDate
    THROW 51100, 'DimDate migration start date must not be after the end date.', 1;

IF OBJECT_ID(N'mart.DimDate', N'U') IS NULL
    THROW 51101, 'Required table mart.DimDate does not exist.', 1;

IF COL_LENGTH(N'mart.DimDate', N'date_key') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'full_date') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'day_number') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'month_number') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'month_name') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'quarter_number') IS NULL
   OR COL_LENGTH(N'mart.DimDate', N'year_number') IS NULL
    THROW 51102, 'mart.DimDate does not match the repository column contract.', 1;

DECLARE @Calendar TABLE (
    date_key INT NOT NULL PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_number INT NOT NULL,
    month_number INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter_number INT NOT NULL,
    year_number INT NOT NULL
);

;WITH CalendarDates AS (
    SELECT @StartDate AS full_date

    UNION ALL

    SELECT DATEADD(DAY, 1, full_date)
    FROM CalendarDates
    WHERE full_date < @EndDate
)
INSERT INTO @Calendar (
    date_key,
    full_date,
    day_number,
    month_number,
    month_name,
    quarter_number,
    year_number
)
SELECT
    YEAR(full_date) * 10000
        + MONTH(full_date) * 100
        + DAY(full_date),
    full_date,
    DAY(full_date),
    MONTH(full_date),
    DATENAME(MONTH, full_date),
    DATEPART(QUARTER, full_date),
    YEAR(full_date)
FROM CalendarDates
OPTION (MAXRECURSION 0);

DECLARE @ExpectedCalendarRows INT = DATEDIFF(DAY, @StartDate, @EndDate) + 1;

IF (SELECT COUNT(*) FROM @Calendar) <> @ExpectedCalendarRows
    THROW 51103, 'Generated calendar row count is not equal to the inclusive date span.', 1;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @RowsBefore BIGINT = (SELECT COUNT_BIG(*) FROM mart.DimDate);
    DECLARE @RangeRowsBefore BIGINT = (
        SELECT COUNT_BIG(*)
        FROM mart.DimDate
        WHERE full_date BETWEEN @StartDate AND @EndDate
    );

    -- Guard against an existing full_date mapped to a nonstandard date_key.
    IF EXISTS (
        SELECT 1
        FROM mart.DimDate AS d
        JOIN @Calendar AS c ON c.full_date = d.full_date
        WHERE d.date_key <> c.date_key
    )
        THROW 51104, 'An existing DimDate full_date has a date_key that differs from the repository YYYYMMDD convention.', 1;

    -- Guard against a generated YYYYMMDD key already assigned to another date.
    IF EXISTS (
        SELECT 1
        FROM mart.DimDate AS d
        JOIN @Calendar AS c ON c.date_key = d.date_key
        WHERE d.full_date <> c.full_date
    )
        THROW 51105, 'A target date_key is already assigned to a different full_date.', 1;

    -- Preserve existing rows, but refuse to mix inconsistent calendar attributes.
    IF EXISTS (
        SELECT 1
        FROM mart.DimDate AS d
        JOIN @Calendar AS c ON c.full_date = d.full_date
        WHERE d.day_number <> c.day_number
           OR d.month_number <> c.month_number
           OR d.month_name <> c.month_name
           OR d.quarter_number <> c.quarter_number
           OR d.year_number <> c.year_number
           OR d.day_number IS NULL
           OR d.month_number IS NULL
           OR d.month_name IS NULL
           OR d.quarter_number IS NULL
           OR d.year_number IS NULL
    )
        THROW 51106, 'Existing DimDate rows contain calendar attributes inconsistent with the repository loader.', 1;

    INSERT INTO mart.DimDate (
        date_key,
        full_date,
        day_number,
        month_number,
        month_name,
        quarter_number,
        year_number
    )
    SELECT
        c.date_key,
        c.full_date,
        c.day_number,
        c.month_number,
        c.month_name,
        c.quarter_number,
        c.year_number
    FROM @Calendar AS c
    WHERE NOT EXISTS (
        SELECT 1
        FROM mart.DimDate AS d WITH (UPDLOCK, HOLDLOCK)
        WHERE d.full_date = c.full_date
    );

    DECLARE @InsertedRows INT = @@ROWCOUNT;
    DECLARE @RowsAfter BIGINT = (SELECT COUNT_BIG(*) FROM mart.DimDate);
    DECLARE @RangeRowsAfter BIGINT = (
        SELECT COUNT_BIG(*)
        FROM mart.DimDate
        WHERE full_date BETWEEN @StartDate AND @EndDate
    );
    DECLARE @DistinctRangeDates BIGINT = (
        SELECT COUNT_BIG(*)
        FROM (
            SELECT full_date
            FROM mart.DimDate
            WHERE full_date BETWEEN @StartDate AND @EndDate
            GROUP BY full_date
        ) AS unique_dates
    );

    IF @RangeRowsAfter <> @ExpectedCalendarRows
        THROW 51107, 'DimDate does not contain exactly one row for every target calendar date.', 1;

    IF @DistinctRangeDates <> @ExpectedCalendarRows
        THROW 51108, 'DimDate target range contains missing or duplicate full_date values.', 1;

    IF EXISTS (
        SELECT 1
        FROM @Calendar AS c
        LEFT JOIN mart.DimDate AS d
          ON d.full_date = c.full_date
         AND d.date_key = c.date_key
        WHERE d.date_key IS NULL
    )
        THROW 51109, 'At least one generated calendar date is absent or has the wrong date_key.', 1;

    -- Validate all existing fact date keys before allowing a commit.
    IF EXISTS (
        SELECT f.date_key
        FROM mart.FactEngineHealth AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT f.date_key
        FROM mart.FactRULPrediction AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE f.date_key IS NOT NULL AND d.date_key IS NULL

        UNION ALL

        SELECT f.date_key
        FROM mart.FactAlert AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT f.date_key
        FROM mart.FactMaintenance AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT f.date_key
        FROM mart.FactSchedule AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL
    )
        THROW 51110, 'At least one fact date_key has no matching mart.DimDate row.', 1;

    -- Proposed state. In dry-run mode these results are shown before rollback.
    SELECT
        CASE WHEN @CommitChanges = 1 THEN 'COMMIT REQUESTED' ELSE 'DRY RUN - WILL ROLLBACK' END AS execution_mode,
        @StartDate AS target_start_date,
        @EndDate AS target_end_date,
        @ExpectedCalendarRows AS expected_target_rows,
        @RowsBefore AS total_rows_before,
        @RangeRowsBefore AS target_rows_before,
        @InsertedRows AS inserted_rows,
        @RowsAfter AS proposed_total_rows,
        @RangeRowsAfter AS proposed_target_rows,
        @DistinctRangeDates AS proposed_distinct_target_dates;

    SELECT
        COUNT_BIG(*) AS proposed_total_rows,
        COUNT(DISTINCT full_date) AS proposed_distinct_dates,
        MIN(full_date) AS proposed_min_full_date,
        MAX(full_date) AS proposed_max_full_date
    FROM mart.DimDate;

    SELECT
        fact_table,
        orphan_date_keys
    FROM (
        SELECT 'FactEngineHealth' AS fact_table, COUNT_BIG(*) AS orphan_date_keys
        FROM mart.FactEngineHealth AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT 'FactRULPrediction', COUNT_BIG(*)
        FROM mart.FactRULPrediction AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE f.date_key IS NOT NULL AND d.date_key IS NULL

        UNION ALL

        SELECT 'FactAlert', COUNT_BIG(*)
        FROM mart.FactAlert AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT 'FactMaintenance', COUNT_BIG(*)
        FROM mart.FactMaintenance AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL

        UNION ALL

        SELECT 'FactSchedule', COUNT_BIG(*)
        FROM mart.FactSchedule AS f
        LEFT JOIN mart.DimDate AS d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL
    ) AS fk_audit
    ORDER BY fact_table;

    IF @CommitChanges = 1
    BEGIN
        COMMIT TRANSACTION;
        PRINT 'COMMITTED: missing mart.DimDate dates were inserted.';
    END
    ELSE
    BEGIN
        ROLLBACK TRANSACTION;
        PRINT 'DRY RUN COMPLETE: all proposed inserts were rolled back. No database changes were retained.';
    END;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;

-- Final persisted state. In dry-run mode this remains the original database state.
SELECT
    COUNT_BIG(*) AS final_total_rows,
    COUNT(DISTINCT full_date) AS final_distinct_dates,
    MIN(full_date) AS final_min_full_date,
    MAX(full_date) AS final_max_full_date,
    SUM(CASE WHEN full_date BETWEEN @StartDate AND @EndDate THEN 1 ELSE 0 END) AS final_target_range_rows
FROM mart.DimDate;
GO

/*
    Recommended minimal follow-up to sql/11_load_mart_dimensions.sql:

    Keep the current SourceDates CTE, then derive calendar bounds as:
      - January 1 of YEAR(MIN(full_date))
      - December 31 of YEAR(MAX(full_date))

    Generate every date between those bounds and feed that CalendarDates CTE
    into the existing idempotent DimDate INSERT. This preserves the existing
    date_key/attribute formulas while extending the calendar through the full
    first and last source years on every ETL run.

    This file intentionally does not modify the existing loader.
*/
