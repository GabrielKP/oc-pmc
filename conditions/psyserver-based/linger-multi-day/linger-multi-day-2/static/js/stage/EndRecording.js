define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  return {
    name: "end_recording",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "end_recording/instruct-1.html",
          // "end_recording/instruct-2.html",
        ],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      // fullscreen handling
      if (study.config["enforce_fullscreen"]) {
        document.documentElement.removeEventListener(
          "fullscreenchange",
          study.fullscreen_enforcer
        );
      }
      if (document.fullscreenElement) {
        document.exitFullscreen();
      }

      pages.next();

      setTimeout(() => {
        // Show upload link
        $("#upload-link").attr("href", study.config.upload_link_day2);
        $("#upload-link").text(study.config.upload_link_day2);

        // Display participant ID
        const participantId = study.data.participantID;
        const studyId = study.data.study_id;
        if (participantId && studyId) {
          console.log(participantId);
          console.log(studyId);
          $("#participant-id").text(participantId);
          $("#study-id").text(studyId);
        }
        // console.log(participantId)
      }, 100);

      // extra binding for agree button
      $("#next").on("click", () => {
        study.data.record_trialdata({
          recording_agree: true,
        });
      });
    },
  };
});
