define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "consent",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["consent.html"], function () {
        if (!study.config["debug"]) {
          $(window).on("beforeunload", function () {
            return "Are you sure you want to leave? You will have to restart the experiment.";
          });
        }
        study.next();
      });
    },
    show: function () {
      // show the page
      pages.next();
      // extra binding for agree button
      $("#next").on("click", () => {
        study.data.record_trialdata({
          consent_agree: true,
        });
      });
      // disagree
      $("#disagree").on("click", () => {
        // record disagreement
        study.data.record_trialdata({
          consent_agree: false,
        });
        // save data
        save_status = study.data.save();
        save_status.then(() => {
          // route to prolific
          window.location.href =
            "https://app.prolific.com/submissions/complete?cc=" +
            study.config["code_noconsent"];
        });
      });
    },
  };
});
