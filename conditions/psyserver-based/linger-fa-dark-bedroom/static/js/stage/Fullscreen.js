define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "fullscreen",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["fullscreen.html"], function () {
        study.next();
      });
    },
    show: function () {
      // show the page
      pages.next();
      // studytime
      $("#studytime").text(study.config["studytime"]);
      // fullscreen button
      if (document.fullscreenElement) {
        // already in fullscreen
        $("#continue").prop("disabled", false);
        $("#continue").on("click", () => {
          pages.next();
        });
      } else {
        $("#fullscreen").on("click", () => {
          document.documentElement.requestFullscreen().then(() => {
            $("#fullscreen").attr("class", "btn btn-success btn-lg");
            $("#continue").attr("class", "btn btn-primary btn-lg");
            $("#continue").prop("disabled", false);
            $("#continue").on("click", () => {
              pages.next();
            });
          });
        });
      }
      // enforce fullscreen
      if (study.config["enforce_fullscreen"]) {
        document.documentElement.addEventListener(
          "fullscreenchange",
          study.fullscreen_enforcer
        );
      }
      // fullscreen button in enforce sceen
      $("#fullscreen-warning").on("click", () => {
        document.documentElement.requestFullscreen();
      });
    },
  };
});
