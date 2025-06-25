define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "reading_endcard",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["reading-endcard.html"], function () {
        study.next();
      });
    },
    show: function () {
      pages.next();
    },
  };
});
