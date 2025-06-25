define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "questionnaire_explanation_stories_black",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "questionnaires/explanation_stories_black_1.html",
          "questionnaires/explanation_stories_black_2.html",
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
