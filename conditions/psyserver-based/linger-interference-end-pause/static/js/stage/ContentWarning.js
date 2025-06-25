define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "content_warning",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["content_warning.html"], function () {
        study.next();
      });
    },
    show: function () {
      // show the page
      pages.next();
      // extra binding for agree button
      $("#next").on("click", () => {
        study.data.record_trialdata({
          content_warning_agree: true,
        });
      });
      // disagree
      $("#disagree").on("click", () => {
        // record disagreement
        study.data.record_trialdata({
          content_warning_agree: false,
        });
        // save data
        save_status = study.data.save();
        save_status.then(() => {
          // route to prolific
          window.location.href =
            "https://app.prolific.com/submissions/complete?cc=" +
            study.config["code_content_warning_disagree"];
        });
      });
    },
  };
});
