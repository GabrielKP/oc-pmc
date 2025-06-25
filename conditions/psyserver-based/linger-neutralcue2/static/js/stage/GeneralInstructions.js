define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "general_instructions",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "general_instructions/instruct-1.html",
          "general_instructions/instruct-2.html",
          "general_instructions/instruct-3.html",
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
