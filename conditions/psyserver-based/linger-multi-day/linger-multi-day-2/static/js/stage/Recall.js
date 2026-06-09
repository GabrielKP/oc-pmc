define(["component/Pages"], function (Pages) {
  return {
    study: null,
    pages: null,
    name: "recall",
    init: function (_study) {
      this.study = _study;
      this.pages = new Pages();
      return this.pages.init(
        this.study,
        [
          "recall/instruct-1.html",
          "recall/instruct-2.html",
          "recall/task.html",
        ],
        function () {
          this.study.next();
        }
      );
    },
    show: function () {
      // show the form
      this.pages.next();
    },
  };
});
