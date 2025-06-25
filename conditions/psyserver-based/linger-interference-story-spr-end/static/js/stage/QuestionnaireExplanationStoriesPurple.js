define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "questionnaire_explanation_stories_purple",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "questionnaires/explanation_stories_purple_1.html",
          "questionnaires/explanation_stories_purple_2.html",
        ],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      pages.next();
    },
  };
});
