require([
  "module/Study",
  "stage/Welcome",
  "stage/ContentWarning",
  "stage/Consent",
  "stage/Fullscreen",
  "stage/GeneralInstructions",
  "stage/FreeAssociationPre",
  "stage/Reading",
  "stage/FreeAssociationPost",
  "stage/QuestionnaireKeywords",
  "stage/QuestionnaireTransportation",
  "stage/QuestionnaireComprehension",
  "stage/QuestionnaireExperience",
  "stage/QuestionnaireDemographics",
  "stage/QuestionnaireOpen",
  "stage/Complete",
], function (
  Study,
  Welcome,
  ContentWarning,
  Consent,
  Fullscreen,
  GeneralInstructions,
  FreeAssociationPre,
  Reading,
  FreeAssociationPost,
  QuestionnaireKeywords,
  QuestionnaireTransportation,
  QuestionnaireComprehension,
  QuestionnaireExperience,
  QuestionnaireDemographics,
  QuestionnaireOpen,
  Complete
) {
  // configuration
  let _version = "1.0.1";
  let config = {
    study: "linger-fa-dark-bedroom",
    version: _version,
    debug: false,
    default_button_timeout: 500,
    time_limit_pre: 180000,
    time_limit_post: 180000,
    code_completion: "CGWO2HA6",
    code_noconsent: "CEH4RWLC",
    code_content_warning_disagree: "CAYTAWD0",
    studytime: 20,
    enforce_fullscreen: true,
    reading_delay_key: 100,
  };

  // determine debug mode
  // The names refer to tom, but should be treated as situation.
  let url_params = new URLSearchParams(window.location.search);
  if (url_params.get("mode") == "debug") {
    config["debug"] = true;
    config["default_button_timeout"] = 0;
    config["time_limit_pre"] = 6000;
    config["time_limit_post"] = 6000;
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

  let initialization = Study.init(
    [
      Welcome,
      ContentWarning,
      Consent,
      Fullscreen,
      GeneralInstructions,
      FreeAssociationPre,
      Reading,
      FreeAssociationPost,
      QuestionnaireKeywords,
      QuestionnaireTransportation,
      QuestionnaireComprehension,
      QuestionnaireExperience,
      QuestionnaireDemographics,
      QuestionnaireOpen,
      Complete,
    ],
    config
  );
  initialization.then(() => {
    Study.next();
  });
});
