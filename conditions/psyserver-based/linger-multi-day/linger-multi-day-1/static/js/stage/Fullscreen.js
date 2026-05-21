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
      $("#studytime_day1").text(study.config["studytime_day1"]);
      // fullscreen button
      if (document.fullscreenElement) {
        // already in fullscreen
        $("#continue").prop("disabled", false);
        $("#continue")
          .off("click")
          .on("click", () => {
            pages.next();
          });
      } else {
        $("#fullscreen")
          .off("click")
          .on("click", () => {
            document.documentElement.requestFullscreen().then(() => {
              $("#fullscreen").attr("class", "btn btn-success btn-lg");
              $("#continue").attr("class", "btn btn-primary btn-lg");
              $("#continue").prop("disabled", false);
              $("#continue")
                .off("click")
                .on("click", () => {
                  pages.next();
                });
            });
          });
      }
      // enforce fullscreen
      if (study.config["enforce_fullscreen"]) {
        // Remove existing listener to prevent accumulation
        document.documentElement.removeEventListener(
          "fullscreenchange",
          study.fullscreen_enforcer
        );
        document.documentElement.addEventListener(
          "fullscreenchange",
          study.fullscreen_enforcer
        );
      }
      // fullscreen button in enforce sceen
      $("#fullscreen-warning")
        .off("click")
        .on("click", () => {
          document.documentElement.requestFullscreen();
        });
    },
  };
});
