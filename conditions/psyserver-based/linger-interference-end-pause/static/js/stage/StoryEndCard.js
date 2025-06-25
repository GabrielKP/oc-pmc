define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "story_endcard",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["story-endcard.html"], function () {
        study.next();
      });
    },
    show: function () {
      pages.next();
    },
  };
});
