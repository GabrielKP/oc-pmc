define(["component/Pages"], function (Pages) {
  return {
    study: null,
    pages: null,
    name: "welcome",
    init: function (_study) {
      this.study = _study;
      this.pages = new Pages();
      return this.pages.init(this.study, ["welcome.html"], function () {
        this.study.next();
      });
    },
    show: function () {
      // show the form
      this.pages.next();
      // version
      $("#version").text(this.study.config["version"]);
    },
  };
});
