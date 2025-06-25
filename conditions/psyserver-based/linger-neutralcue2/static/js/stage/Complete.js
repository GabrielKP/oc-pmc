define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "complete",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["complete.html"], function () {
        study.next();
      });
    },
    show: function () {
      // fullscreen handling
      if (study.config["enforce_fullscreen"]) {
        document.documentElement.removeEventListener(
          "fullscreenchange",
          study.fullscreen_enforcer
        );
        if (document.fullscreenElement) {
          document.exitFullscreen();
        }
      }
      if (!study.config["debug"]) {
        $(window).off("beforeunload");
      }
      // show the html
      pages.next();
      // handle data saving
      show_success_complete_screen = () => {
        $("#card-complete").show();
        $("#complete").on("click", () => {
          window.location.href =
            "https://app.prolific.co/submissions/complete?cc=" +
            study.config["code_completion"];
        });
      };
      save_status = study.data.save();
      // let participants retry submission once.
      save_status.then(show_success_complete_screen, () => {
        $("#card-resubmit").show();
        $("#resubmit").on("click", () => {
          resubmit_status = study.data.save();
          resubmit_status.then(show_success_complete_screen, () => {
            $("#card-resubmit").hide();
            $("#card-download").show();
            $("#download").on("click", () => {
              study.data.save((download = true));
              show_success_complete_screen();
            });
          });
        });
      });
    },
  };
});
