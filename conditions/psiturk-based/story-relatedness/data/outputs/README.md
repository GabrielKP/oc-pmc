# ratings.zip

Rating data extracted from raw datafiles.

Following files are contained (x = theme or x = moment):

- `x_raw.csv`: individual ratings
- `x.csv`: mean ratings
- `x_median.csv`: median ratings
- `x_count.csv`: word counts
- `x_variance.csv`: word variances
- `overview.txt`: file with some overview statistics
- `README.md`

Each file has a header in the first row (e.g. word,variance).

Moment words (event-related words may be a better fitting name) were rated
on this question:

- How related is the word to a specific moment within the story?
  (e.g. the word reminds you of specific details in the story)

Theme words were rated independently from each other based on this question:

- How related is the word to the general theme or mood of the story?
  (e.g. you feel the word is related, even though not to a specific moment)

# plots.zip

Contains various basic histograms and plots.
To interactively plot all moment vs theme ratings open
`scatter_themme_moment.html` in your browser
