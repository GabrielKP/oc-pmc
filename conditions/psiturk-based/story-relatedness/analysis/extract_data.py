import argparse
import os

from overview import load_data


def extract_data(study_dir: str):
    output_dir = "outputs"
    # load
    trialdata, _, _ = load_data(study_dir=study_dir)

    # get data
    theme_ratings = trialdata[
        (trialdata["phase"] == "rating")
        & (trialdata["status"] == "ongoing")
        & (trialdata["question_type"] == "theme")
    ]
    theme_ratings = theme_ratings[["word", "response"]].reset_index(drop=True)
    moment_ratings = trialdata[
        (trialdata["phase"] == "rating")
        & (trialdata["status"] == "ongoing")
        & (trialdata["question_type"] == "moment")
    ]
    moment_ratings = moment_ratings[["word", "response"]].reset_index(drop=True)

    theme_grouped = theme_ratings.groupby("word")
    theme_ratings_mean = theme_grouped.mean().reset_index()
    theme_ratings_mean = theme_ratings_mean.rename(
        columns={"response": "mean_rating"}
    )
    theme_ratings_median = theme_grouped.median().reset_index()
    theme_ratings_median = theme_ratings_median.rename(
        columns={"response": "median_rating"}
    )
    theme_ratings_count = theme_grouped.count().reset_index()
    theme_ratings_count = theme_ratings_count.rename(
        columns={"response": "count"}
    )
    theme_ratings_variance = theme_grouped.var().reset_index()
    theme_ratings_variance = theme_ratings_variance.rename(
        columns={"response": "variance"}
    )

    moment_grouped = moment_ratings.groupby("word")
    moment_ratings = moment_ratings.rename(columns={"response": "rating"})
    moment_ratings_mean = moment_grouped.mean().reset_index()
    moment_ratings_mean = moment_ratings_mean.rename(
        columns={"response": "mean_rating"}
    )
    moment_ratings_median = moment_grouped.median().reset_index()
    moment_ratings_median = moment_ratings_median.rename(
        columns={"response": "median_rating"}
    )
    moment_ratings_count = moment_grouped.count().reset_index()
    moment_ratings_count = moment_ratings_count.rename(
        columns={"response": "count"}
    )
    moment_ratings_variance = moment_grouped.var().reset_index()
    moment_ratings_variance = moment_ratings_variance.rename(
        columns={"response": "variance"}
    )

    if not os.path.exists(os.path.join(study_dir, output_dir)):
        os.makedirs(os.path.join(study_dir, output_dir))
    # save
    theme_ratings.to_csv(
        os.path.join(study_dir, output_dir, "theme_raw.csv"),
        header=True,
        index=False,
    )
    theme_ratings_mean.to_csv(
        os.path.join(study_dir, output_dir, "theme.csv"),
        header=True,
        index=False,
    )
    theme_ratings_median.to_csv(
        os.path.join(study_dir, output_dir, "theme_median.csv"),
        header=True,
        index=False,
    )
    theme_ratings_count.to_csv(
        os.path.join(study_dir, output_dir, "theme_count.csv"),
        header=True,
        index=False,
    )
    theme_ratings_variance.to_csv(
        os.path.join(study_dir, output_dir, "theme_variance.csv"),
        header=True,
        index=False,
    )
    moment_ratings.to_csv(
        os.path.join(study_dir, output_dir, "moment_raw.csv"),
        header=True,
        index=False,
    )
    moment_ratings_mean.to_csv(
        os.path.join(study_dir, output_dir, "moment.csv"),
        header=True,
        index=False,
    )
    moment_ratings_median.to_csv(
        os.path.join(study_dir, output_dir, "moment_median.csv"),
        header=True,
        index=False,
    )
    moment_ratings_count.to_csv(
        os.path.join(study_dir, output_dir, "moment_count.csv"),
        header=True,
        index=False,
    )
    moment_ratings_variance.to_csv(
        os.path.join(study_dir, output_dir, "moment_variance.csv"),
        header=True,
        index=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="extract data")
    parser.add_argument(
        "-s",
        "--study_dir",
        type=str,
        default="data",
        help="Directory for study",
    )
    args = parser.parse_known_args()[0]
    extract_data(study_dir=args.study_dir)
