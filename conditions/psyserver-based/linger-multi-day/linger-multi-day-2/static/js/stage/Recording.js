define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "recording",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "recording/instruct-1.html",
          "recording/instruct-2.html",
          "recording/instruct-3.html",
          "recording/instruct-4.html",
        ],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      pages.next();

      // extra binding for agree button
      $("#next").on("click", () => {
        study.data.record_trialdata({
          recording_agree: true,
        });
      });
    },
  };
});
