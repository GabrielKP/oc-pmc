define(["component/Pages"], function (Pages) {
  let study;
  let page1;
  let page2;
  return {
    name: "study_instructions",
    init: function (_study) {
      study = _study;
      page1 = new Pages();
      page2 = new Pages();
      return Promise.all([
        page1.init(study, ["study_instructions/instruct-1.html"], function () {
          page2.reset();
          page2.next();
          setTimeout(() => {
            $("#stop").prop("disabled", false);
          }, study.config.default_button_timeout);
          // binding for previous button
          $("#prevC").on("click", () => {
            page1.reset();
            page1.next();
            // set study time
            $("#studytime_day1").text(study.config["studytime_day1"]);
            $("#studytime_day2").text(study.config["studytime_day2"]);
          });
          // binding for agree button
          $("#next").on("click", () => {
            study.data.record_trialdata({
              comultiple_days_agreensent_agree: true,
            });
          });
          // disagree
          $("#stop").on("click", () => {
            // record disagreement
            study.data.record_trialdata({
              multiple_days_agree: false,
            });
            // save data
            const save_status = study.data.save();
            save_status.then(() => {
              // route to prolific
              window.location.href =
                "https://app.prolific.co/submissions/complete?cc=" +
                study.config["code_multiple_days_disagree"];
            });
          });
        }),
        page2.init(study, ["study_instructions/instruct-2.html"], function () {
          study.next();
        }),
      ]);
    },
    show: function () {
      // show the page
      page1.next();
      // set study time
      $("#studytime_day1").text(study.config["studytime_day1"]);
      $("#studytime_day2").text(study.config["studytime_day2"]);
    },
  };
});
