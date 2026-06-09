require([
  "module/Study",
  "stage/Welcome",
  "stage/ContentWarning",
  "stage/Consent",
  "stage/StudyInstructions",
  "stage/Recording",
  "stage/Fullscreen",
  "stage/GeneralInstructions",
  "stage/FreeAssociationPre",
  "stage/Reading",
  "stage/FreeAssociationPost",
  "stage/QuestionnaireTransportation",
  "stage/QuestionnaireComprehension",
  "stage/QuestionnaireExperience",
  "stage/QuestionnaireDemographics",
  "stage/QuestionnaireOpen",
  "stage/EndRecording",
  "stage/Complete",
], function (
  Study,
  Welcome,
  ContentWarning,
  Consent,
  StudyInstructions,
  Recording,
  Fullscreen,
  GeneralInstructions,
  FreeAssociationPre,
  Reading,
  FreeAssociationPost,
  QuestionnaireTransportation,
  QuestionnaireComprehension,
  QuestionnaireExperience,
  QuestionnaireDemographics,
  QuestionnaireOpen,
  EndRecording,
  Complete
) {
  // configuration
  let _version = "1.0.0-alpha13";
  let config = {
    study: "multi-day-1",
    version: _version,
    debug: false,
    default_button_timeout: 500,
    time_limit_fa: 180000,
    code_completion: "CGWO2HA6",
    code_noconsent: "CEH4RWLC",
    code_content_warning_disagree: "CAYTAWD0",
    code_multiple_days_disagree: "C1GM2ANK",
    studytime_day1: 45,
    studytime_day2: 55,
    enforce_fullscreen: true,
    reading_delay_key: 100,
    upload_link_day1:
      "https://livejohnshopkins-my.sharepoint.com/:f:/g/personal/gkressi1_jh_edu/IgBxq1EEe_7lTYnVY9tCPLd_ASkG55VT3wET2UrnnZ-q4tA",
  };

  // determine debug mode
  let url_params = new URLSearchParams(window.location.search);
  if (url_params.get("mode") == "debug") {
    config["debug"] = true;
    config["default_button_timeout"] = 0;
    config["time_limit_fa"] = 6000;
    config["enforce_fullscreen"] = false;
  }

  // local mode: needed to determine how data is saved
  config["local"] = false;
  if (url_params.has("local")) {
    config["local"] = true;
  }

  // skip button for debug
  if (config["debug"]) {
    $("#container-skip-button").show();
    $("#skip").on("click", () => {
      if (Study.current_stage.finish_task != null) {
        Study.current_stage.finish_task(true);
      } else {
        Study.next();
      }
    });
  }

  // General experiment flow
  // Day 1: FA1 -> Reading -> FA2 -> Questionnaire -> End
  // Day 2: FA3 -> Recall -> FA4 -> Reading -> FA5 ->Questionnaire -> End
  let initialization = Study.init(
    [
      Welcome,
      ContentWarning,
      Consent,
      StudyInstructions,
      Recording,
      Fullscreen,
      GeneralInstructions,
      FreeAssociationPre,
      Reading,
      FreeAssociationPost,
      QuestionnaireTransportation,
      QuestionnaireComprehension,
      QuestionnaireExperience,
      QuestionnaireDemographics,
      QuestionnaireOpen,
      EndRecording,
      Complete,
    ],
    config
  );
  initialization.then(() => {
    Study.next();
  });
});
