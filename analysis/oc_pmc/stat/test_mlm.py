from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.formula.api as smf
from plotly.subplots import make_subplots
from scipy import stats
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
from statsmodels.regression.mixed_linear_model import MixedLMResults

from oc_pmc import console, get_logger
from oc_pmc.load import (
    load_rated_wordchains,
    load_thought_entries_and_questionnaire,
    load_wordchains,
)
from oc_pmc.utils import (
    add_config_columns,
    add_dummy_thought_entries,
    cut_small_value,
    save_plot,
)

log = get_logger(__name__)


def check_model_assumptions(
    config: dict, result: MixedLMResults, aggregated_df: pd.DataFrame
):
    """Check mixed-effects model assumptions and generate plots"""

    console.print("\nChecking model assumptions", style="blue")

    # Extract residuals and fitted values
    fitted_values: pd.Series = result.fittedvalues
    residuals: pd.Series = result.resid

    fig_assumptions = make_subplots(
        rows=5,
        cols=2,
        row_titles=[
            "1. Linearity of fixed effects",
            "2. Normality of residuals",
            "3. Homoscedasticity",
            "4. Normality of random effects",
            "5. Independence of residuals",
        ],
        subplot_titles=(
            "1: Residuals vs Fitted Values",
            "1: Residuals vs bin-time",
            "2: Q-Q Plot: Residual normality",
            "2: Distribution of Residuals",
            "3: Absolute Residuals vs Fitted",
            "3: Squared Residuals vs Fitted",
            "4: Random intercepts distribution",
            "4: Random slopes distribution",
            "5: Durbin-Watson Statistics Distribution",
        ),
        # vertical_spacing=0.2,
    )

    ### 1. -----------------------------------------------------------------
    console.print("\n1. Linearity of fixed effects", style="green")

    # Create interactive subplot figure
    # fig_linearity = make_subplots(
    #     rows=1,
    #     cols=2,
    #     subplot_titles=("Residuals vs Fitted Values", "Residuals vs Time"),
    #     horizontal_spacing=0.1,
    # )

    # Residuals vs fitted double presses
    fig_assumptions.add_trace(
        go.Scatter(
            x=fitted_values,
            y=residuals,
            mode="markers",
            marker=dict(size=6, opacity=0.6, color="blue"),
            name="Residuals",
        ),
        row=1,
        col=1,
    )

    # Add trendline
    # X = fitted_values.to_numpy().reshape(-1, 1)  # Reshape for sklearn
    # y = residuals

    # # Fit linear regression
    # lr = LinearRegression()
    # lr.fit(X, y)

    # # Generate trendline points
    # x_trend = np.linspace(fitted_values.min(), fitted_values.max(), 100)
    # y_trend = lr.predict(x_trend.reshape(-1, 1))

    # # Add red trendline
    # fig_assumptions.add_trace(
    #     go.Scatter(
    #         x=x_trend,
    #         y=y_trend,
    #         mode="lines",
    #         line=dict(color="red", width=3),
    #         name="Trendline",
    #     ),
    #     row=1,
    #     col=1,
    # )

    # Add horizontal line at y=0
    fig_assumptions.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=1)  # type: ignore

    if len(fitted_values) > 10:
        sorted_idx = np.argsort(fitted_values)
        window_length = min(51, len(residuals) // 3)
        if window_length % 2 == 0:
            window_length += 1
        if window_length >= 3:
            smoothed = savgol_filter(residuals.iloc[sorted_idx], window_length, 3)
            fig_assumptions.add_trace(
                go.Scatter(
                    x=fitted_values.iloc[sorted_idx],
                    y=smoothed,
                    mode="lines",
                    line=dict(color="red", width=3),
                    name="Trend",
                    hovertemplate="Trend line<extra></extra>",
                ),
                row=1,
                col=1,
            )

    # Residuals vs Time
    fig_assumptions.add_trace(
        go.Scatter(
            x=aggregated_df["bin_time"],
            y=residuals,
            mode="markers",
            marker=dict(size=6, opacity=0.6, color="green"),
            name="Time Residuals",
            hovertemplate="Time: %{x}<br>Residual: %{y:.3f}<extra></extra>",
        ),
        row=1,
        col=2,
    )
    fig_assumptions.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=2)  # type: ignore

    # Add trendline
    X = aggregated_df["bin_time"].to_numpy().reshape(-1, 1)  # Reshape for sklearn
    y = residuals

    # Fit linear regression
    lr = LinearRegression()
    lr.fit(X, y)

    # Generate trendline points
    x_trend = np.linspace(
        aggregated_df["bin_time"].min(), aggregated_df["bin_time"].max(), 100
    )
    y_trend = lr.predict(x_trend.reshape(-1, 1))

    # Add red trendline
    fig_assumptions.add_trace(
        go.Scatter(
            x=x_trend,
            y=y_trend,
            mode="lines",
            line=dict(color="red", width=3),
            name="Trend",
        ),
        row=1,
        col=2,
    )

    fig_assumptions.update_xaxes(title_text="Fitted Values", row=1, col=1)
    fig_assumptions.update_xaxes(title_text="Time", row=1, col=2)
    fig_assumptions.update_yaxes(title_text="Residuals", row=1, col=1)
    fig_assumptions.update_yaxes(title_text="Residuals", row=1, col=2)

    console.print(">> Check for random scatter around y=0 and no general patterns")

    ### 2. -----------------------------------------------------------------
    console.print("\n2. Normality of residuals", style="green")

    # Statistical tests for normality
    shapiro_stat, shapiro_p = stats.shapiro(residuals)
    console.print(f"Wilk-Shapiro test: W = {shapiro_stat:.4f}, p = {shapiro_p:.4f}")

    if shapiro_p > 0.05:
        console.print(">> Residuals appear normally distributed (p > 0.05")
    else:
        console.print(">> Residuals may violate normality (p < 0.05)", style="red")

    # Q-Q plot

    qq_results = stats.probplot(residuals, dist="norm")
    theoretical_quantiles = qq_results[0][0]
    sample_quantiles = qq_results[0][1]

    fig_assumptions.add_trace(
        go.Scatter(
            x=theoretical_quantiles,
            y=sample_quantiles,
            mode="markers",
            marker=dict(size=6, color="blue", opacity=0.7),
            name="Q-Q Points",
            hovertemplate="Theoretical: %{x:.3f}<br>Sample: %{y:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add reference line for Q-Q plot
    min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
    max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
    fig_assumptions.add_trace(
        go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Perfect Normal",
            hovertemplate="Perfect normal line<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Histogram with normal overlay
    fig_assumptions.add_trace(
        go.Histogram(
            x=residuals,
            nbinsx=20,
            histnorm="probability density",
            name="Residuals",
            opacity=0.7,
            marker_color="lightblue",
            hovertemplate="Bin: %{x}<br>Density: %{y:.4f}<extra></extra>",
        ),
        row=2,
        col=2,
    )

    # Overlay normal distribution
    x_normal = np.linspace(residuals.min(), residuals.max(), 100)
    y_normal = stats.norm.pdf(x_normal, residuals.mean(), residuals.std())
    fig_assumptions.add_trace(
        go.Scatter(
            x=x_normal,
            y=y_normal,
            mode="lines",
            line=dict(color="red", width=3),
            name="Normal Distribution",
            hovertemplate="Normal curve<extra></extra>",
        ),
        row=2,
        col=2,
    )

    fig_assumptions.update_xaxes(title_text="Theoretical Quantiles", row=2, col=1)
    fig_assumptions.update_xaxes(title_text="Residuals", row=2, col=2)
    fig_assumptions.update_yaxes(title_text="Sample Quantiles", row=2, col=1)
    fig_assumptions.update_yaxes(title_text="Density", row=2, col=2)

    ### 3. -----------------------------------------------------------------
    console.print("\n3. Homoscedasticity (constant variance of errors)", style="green")

    abs_residuals = np.abs(residuals)
    squared_residuals = residuals**2

    # Test correlation
    corr_abs, p_abs = stats.pearsonr(fitted_values, abs_residuals)
    console.print(
        f"Correlation fitted vs |residuals|: r = {corr_abs:.4f}, p = {p_abs:.4f}"
    )

    if p_abs > 0.05:  # type: ignore
        console.print(">> Homoscedasticity assumption likely satisfied")
    else:
        console.print(">> Possible heteroscedasticity detected", style="red")

    # Absolute residuals vs fitted
    fig_assumptions.add_trace(
        go.Scatter(
            x=fitted_values,
            y=abs_residuals,
            mode="markers",
            marker=dict(size=6, opacity=0.6, color="blue"),
            name="|Residuals|",
            hovertemplate="Fitted: %{x:.3f}<br>|Residual|: %{y:.3f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    # Add trend line for absolute residuals
    z = np.polyfit(fitted_values, abs_residuals, 1)
    p_poly = np.poly1d(z)
    fig_assumptions.add_trace(
        go.Scatter(
            x=fitted_values,
            y=p_poly(fitted_values),
            mode="lines",
            line=dict(color="red", dash="dash", width=2),
            name="Trend Line",
            hovertemplate="Trend line<extra></extra>",
        ),
        row=3,
        col=1,
    )

    # Squared residuals vs fitted
    fig_assumptions.add_trace(
        go.Scatter(
            x=fitted_values,
            y=squared_residuals,
            mode="markers",
            marker=dict(size=6, opacity=0.6, color="green"),
            name="Residuals²",
            hovertemplate="Fitted: %{x:.3f}<br>Residual²: %{y:.3f}<extra></extra>",
        ),
        row=3,
        col=2,
    )

    fig_assumptions.update_xaxes(title_text="Fitted Values", row=3, col=1)
    fig_assumptions.update_xaxes(title_text="Fitted Values", row=3, col=2)
    fig_assumptions.update_yaxes(title_text="|Residuals|", row=3, col=1)
    fig_assumptions.update_yaxes(title_text="Squared Residuals", row=3, col=2)

    ### 4. -----------------------------------------------------------------
    console.print("\n4. Normality of random effects", style="green")

    # Extract random effects
    random_effects = result.random_effects
    random_intercepts = []
    random_slopes = []

    for _, effects in random_effects.items():
        if "Group" in effects:
            random_intercepts.append(effects["Group"])
        if "bin_time" in effects:
            random_slopes.append(effects["bin_time"])

    # Test normality of random intercepts

    if random_intercepts:
        shapiro_stat, shapiro_p = stats.shapiro(random_intercepts)
        console.print(
            f">> Random intercepts normality:"
            f" W = {shapiro_stat:.4f}, p = {shapiro_p:.4f}"
        )

        if shapiro_p > 0.05:
            console.print(">> Random intercepts appear normally distributed (p > 0.05")
        else:
            console.print(
                ">> Random intercepts may violate normality (p < 0.05)", style="red"
            )

        fig_assumptions.add_trace(
            go.Histogram(
                x=random_intercepts,
                nbinsx=15,
                name="Random Intercepts",
                opacity=0.7,
                marker_color="blue",
                hovertemplate="Intercept: %{x:.3f}<br>Count: %{y}<extra></extra>",
            ),
            row=4,
            col=1,
        )

        fig_assumptions.update_xaxes(title_text="Random intercepts", row=4, col=1)
        fig_assumptions.update_yaxes(title_text="Frequency", row=4, col=1)

    # Test normality of random slopes
    if random_slopes:
        shapiro_stat, shapiro_p = stats.shapiro(random_slopes)
        console.print(
            f">> Random slopes normality: W = {shapiro_stat:.4f}, p = {shapiro_p:.4f}"
        )

        if shapiro_p > 0.05:
            console.print(">> Random slopes appear normally distributed (p > 0.05")
        else:
            console.print(
                ">> Random slopes may violate normality (p < 0.05)", style="red"
            )

        fig_assumptions.add_trace(
            go.Histogram(
                x=random_slopes,
                nbinsx=15,
                name="Random Slopes",
                opacity=0.7,
                marker_color="green",
                hovertemplate="Slope: %{x:.3f}<br>Count: %{y}<extra></extra>",
            ),
            row=4,
            col=2,
        )
        fig_assumptions.update_xaxes(title_text="Random slopes", row=4, col=2)
        fig_assumptions.update_yaxes(title_text="Frequency", row=4, col=2)

    fig_assumptions.update_layout(barmode="overlay")

    ### 5. -----------------------------------------------------------------
    console.print("\n5. Independence of residuals", style="green")

    # Check for temporal autocorrelation within participants
    autocorr_results = []

    for pID in aggregated_df["participantID"].unique():
        participant_residuals = residuals[aggregated_df["participantID"] == pID]

        # Durbin-Watson approximation
        dw_stat = np.sum(np.diff(participant_residuals) ** 2) / np.sum(
            participant_residuals**2
        )
        autocorr_results.append(dw_stat)

    mean_dw = np.mean(autocorr_results)
    console.print(f">> Mean Durbin-Watson statistic: {mean_dw:.4f}")
    console.print(
        ">> DW interpretation: ~2.0=no autocorr, <1.5 or >2.5=possible autocorr"
    )

    if 1.5 <= mean_dw <= 2.5:
        console.print(">> Independence assumption likely satisfied")
    else:
        console.print(">> Possible autocorrelation in residuals", style="red")

    # Create Durbin-Watson distribution plot
    fig_assumptions.add_trace(
        go.Histogram(
            x=autocorr_results,
            nbinsx=15,
            name="DW Statistics",
            marker_color="lightblue",
            opacity=0.7,
            hovertemplate="DW Stat: %{x:.3f}<br>Count: %{y}<extra></extra>",
        ),
        row=5,
        col=1,
    )

    # Add reference lines
    fig_assumptions.add_vline(
        x=mean_dw,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Mean: {mean_dw:.3f}",
        row=5,  # type: ignore
        col=1,  # type: ignore
    )
    fig_assumptions.add_vline(
        x=2.0,
        line_dash="dot",
        line_color="green",
        annotation_text="Ideal: 2.0",
        annotation_position="bottom right",
        row=5,  # type: ignore
        col=1,  # type: ignore
    )

    fig_assumptions.update_xaxes(title_text="Durbin-Watson Statistic", row=5, col=1)
    fig_assumptions.update_yaxes(title_text="Frequency", row=5, col=1)

    ### 6. -----------------------------------------------------------------
    console.print("\n6. Number of outliers", style="green")

    # Calculate standardized residuals
    residual_std = residuals.std()
    standardized_residuals = residuals / residual_std

    # Identify potential outliers
    outliers = np.abs(standardized_residuals) > 2.5
    n_outliers = np.sum(outliers)

    console.print(f"Potential outliers (|std residual| > 2.5): {n_outliers}")
    console.print(f"Percentage of outliers: {100 * n_outliers / len(residuals):.1f}%")

    if n_outliers > len(residuals) * 0.05:  # More than 5% outliers
        console.print(">> High proportion of outliers detected", style="red")
    else:
        console.print(">> Acceptable proportion of outliers")

    # -------------------------------
    # Finish plot

    assumptions_height = config.get("assumptions_height", 2400)
    assumptions_width = config.get("assumptions_width", 1200)

    fig_assumptions.update_layout(
        width=assumptions_width,  # Width in pixels
        height=assumptions_height,  # Height in pixels
        title="Model Assumptions Diagnostic Plots",  # Optional overall title
    )

    if config.get("assumptions_show", False):
        fig_assumptions.show()

    if config["assumptions_save"]:
        filename = config["comparison_category"]
        transform = config.get("transform", "") or ""
        if transform != "":
            filename += f"_{transform}"
        plot_path = Path(
            config.get("study", ""),
            "mlm_assumptions",
            config["measure"],
            f"{filename}.pdf",
        )
        assumptions_config = {
            "width": assumptions_width,
            "height": assumptions_height,
            "scale": config.get("assumptions_scale"),
        }
        print("")
        save_plot(
            assumptions_config,
            fig_assumptions,
            plot_path,
        )


def test_mlm(config: dict):
    """Runs a mixed-linear-model on config, outputs in terminal and as latex."""

    measure = config["measure"]
    comparison_category = config["comparison_category"]
    step = config["step"]
    x_column = "timestamp" if not config.get("x_column") else config["x_column"]
    model_kind = config.get("model_kind", "slopes")  # slopes | simple
    model_method = config.get(
        "model_method", None
    )  # https://www.statsmodels.org/dev/generated/statsmodels.regression.mixed_linear_model.MixedLM.fit.html#statsmodels.regression.mixed_linear_model.MixedLM.fit
    pvalue_exact = config.get("pvalue_exact", False)
    threshold = config.get("threshold", 0.05)
    transform = config.get("transform", "") or ""

    if config.get("name1") and config.get("name2"):
        console_comment = config.get("console_comment", "")
        console.print(
            f"\n > Test_two: {measure}: {config['name1']} v"
            f" {config['name2']}{console_comment}",
            style="yellow",
        )

    # define columns to add to config
    config_columns = ["story", "condition", "position"]
    if config.get("additional_grouping_columns"):
        config_columns += config["additional_grouping_columns"]

    # load appropriate data
    config1 = {**config, **config["config1"]}
    config2 = {**config, **config["config2"]}
    if measure == "story_relatedness":
        data1_df = load_rated_wordchains(config1)[["story_relatedness", "timestamp"]]
        data2_df = load_rated_wordchains(config2)[["story_relatedness", "timestamp"]]
    elif measure == "word_time":
        data1_df = load_wordchains(config1)[["word_time", "timestamp"]]
        data2_df = load_wordchains(config2)[["word_time", "timestamp"]]
    elif measure == "thought_entries":
        data1_df, quest1_df = load_thought_entries_and_questionnaire(config1)
        data2_df, quest2_df = load_thought_entries_and_questionnaire(config2)

        # need to add dummy id's for pIDs who did not submit a TE
        data1_df = add_dummy_thought_entries(data1_df, quest1_df)
        data2_df = add_dummy_thought_entries(data2_df, quest2_df)
    else:
        raise ValueError(f"Invalid measure:'{measure}'")

    # add story & position column back in
    data1_df = add_config_columns(
        config=config1, data_df=data1_df, config_columns=config_columns
    )
    data2_df = add_config_columns(
        config=config2, data_df=data2_df, config_columns=config_columns
    )
    data_df = pd.concat((data1_df, data2_df))

    if not config.get("comparison_within_participants", False):
        raise NotImplementedError(
            "Can only handle within participant comparisons at the moment"
        )

    if config.get("replace_columns") is not None:
        for colname, col_replace_dct in config["replace_columns"].items():
            if not isinstance(col_replace_dct, dict):
                raise ValueError(
                    f"col_replace_dct has to be a dct not: {type(col_replace_dct)}"
                )
            data_df[colname] = data_df[colname].replace(col_replace_dct)

    # update grouping columns
    grouping_columns = ["story", "condition", "participantID", "position", "bins"]
    if config.get("additional_grouping_columns"):
        grouping_columns += config["additional_grouping_columns"]

    # Need to determine min x value: take closest multiple to "step"
    min_x = config.get(
        "min_x",
        (min(data_df[x_column]) // step) * step,
    )
    max_x = config.get(
        "max_x",
        # accomodate largest value                          | not sure why
        int(np.ceil(max(data_df[x_column]) / step)) * step + step - 1,
    )

    # bin
    bins = np.arange(min_x, max_x + 1, step)
    n_bins = len(bins) - 1
    step_s = step // 1000
    bin_labels = [i * step_s + step_s // 2 for i in range(n_bins)]
    data_df["bins"] = pd.cut(data_df[x_column], bins=bins, labels=bin_labels)

    family = None
    outcome_name = ""
    if measure == "thought_entries":
        aggregated_df = (
            data_df.groupby(grouping_columns, observed=False)[["double_press"]]
            .count()
            .reset_index()
        )
        outcome_name = "double_press"
    else:
        raise NotImplementedError(f"Script not implemented for {measure=}")

    aggregated_df.loc[:, "bin_time"] = aggregated_df["bins"].astype(int)

    aggregated_df["log_double_press"] = np.log(aggregated_df["double_press"] + 1)
    aggregated_df["sqrt_double_press"] = np.sqrt(aggregated_df["double_press"])
    assert transform in ["", "log", "sqrt"], "Invalid transform"

    print("Head:")
    print(aggregated_df.head(10))
    print(f"Shape: {aggregated_df.shape}")
    print(f"Types:\n{aggregated_df.dtypes}")

    if transform != "":
        outcome_name = f"{transform}_{outcome_name}"
    if model_kind == "simple":
        model = smf.mixedlm(
            f"{outcome_name} ~ bin_time * {comparison_category}",
            aggregated_df,
            groups=aggregated_df["participantID"],
            family=family,
        )
        result = model.fit(method=model_method)
        console.print("\nRandom intercepts results", style="blue")

    elif model_kind == "slopes":
        model = smf.mixedlm(
            f"{outcome_name} ~ bin_time * {comparison_category}",
            aggregated_df,
            groups=aggregated_df["participantID"],
            re_formula="~bin_time",
        )
        result = model.fit(method=model_method)
        console.print("\nRandom intercepts & slopes results", style="blue")
    else:
        raise ValueError(f"Not valid {model_kind=}")

    print(result.summary())
    # get interaction term
    # determine interaction parameter name
    interaction_val_name = list(
        set(aggregated_df[comparison_category].unique()).difference(
            [aggregated_df[comparison_category].iloc[0]]
        )
    )[0]
    param_interaction = f"bin_time:{comparison_category}[T.{interaction_val_name}]"

    interaction_coef = result.params.loc[param_interaction]
    interaction_z = result.tvalues.loc[param_interaction]
    interaction_pvalue = result.pvalues.loc[param_interaction]

    if pvalue_exact:
        interaction_p_str = f"p = {f'{interaction_pvalue:f}'[1:]}"
    elif interaction_pvalue < (threshold - 0.2 * threshold):
        interaction_p_str = f"p < {threshold}".replace("0.", ".")
    else:
        # find
        if interaction_pvalue < 0.09:
            interaction_p_str = f"p = {cut_small_value(interaction_pvalue)}"
        else:
            interaction_p_str = f"p = {str(round(interaction_pvalue, 2))[1:]}"

    interaction_coef_str = cut_small_value(interaction_coef)

    print(
        "\nInteraction:"
        f" ($\\beta = {interaction_coef_str},"
        f" z = {interaction_z:.2f},"
        f" {interaction_p_str}$)"
    )

    if config.get("latex"):
        console.print("\nTable in latex", style="blue")
        print(result.summary().as_latex())

    # check assumptions
    check_model_assumptions(
        config,
        result=result,  # type: ignore
        aggregated_df=aggregated_df,
    )


if __name__ == "__main__":
    TIMEFILTER = ("filter", {"exclude": [("gte", "timestamp", 180000)]})
    NOFILTER = ("filter", {})

    test_mlm(
        {
            "config1": {"position": "pre"},
            "config2": {"position": "post"},
            "exclude": ("gt", "timestamp", 180000),
            "story": "carver_original",
            "condition": "button_press",
            "measure": "thought_entries",
            "step": 30000,
            "comparison_category": "position",
            "comparison_within_participants": True,
            "replace_columns": {
                "position": {"post": "Story thought", "pre": "Food thoughts"}
            },
            "transform": "sqrt",
            "model_kind": "slopes",
            "model_method": "powell",
            "assumptions_save": True,
            "assumptions_width": 1200,
            "assumptions_height": 2400,
        }
    )
