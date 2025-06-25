require([
  "module/Study",
  "stage/Welcome",
  "stage/ContentWarning",
  "stage/Consent",
  "stage/Fullscreen",
  "stage/GeneralInstructions",
  "stage/InterferenceReadingTraining",
  "stage/FreeAssociationPre",
  "stage/Reading",
  "stage/InterferenceReadingTesting",
  "stage/FreeAssociationPost",
  "stage/QuestionnaireExplanationStoriesBlack",
  "stage/QuestionnaireTransportation",
  "stage/QuestionnaireComprehension",
  "stage/QuestionnaireExperience",
  "stage/QuestionnaireExplanationStoriesPurple",
  "stage/QuestionnaireTransportationInterference",
  "stage/QuestionnaireComprehensionInterference",
  "stage/QuestionnaireExperienceInterference",
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
  InterferenceReadingTraining,
  FreeAssociationPre,
  Reading,
  InterferenceReadingTesting,
  FreeAssociationPost,
  QuestionnaireExplanationStoriesBlack,
  QuestionnaireTransportation,
  QuestionnaireComprehension,
  QuestionnaireExperience,
  QuestionnaireExplanationStoriesPurple,
  QuestionnaireTransportationInterference,
  QuestionnaireComprehensionInterference,
  QuestionnaireExperienceInterference,
  QuestionnaireDemographics,
  QuestionnaireOpen,
  Complete
) {
  // configuration
  let _version = "1.0.0";
  let config = {
    study: "linger-interference-story-spr",
    version: _version,
    debug: false,
    default_button_timeout: 500,
    time_limit_pre: 180000,
    time_limit_post: 180000,
    code_completion: "CGWO2HA6",
    code_noconsent: "CEH4RWLC",
    code_content_warning_disagree: "CAYTAWD0",
    studytime: 36,
    enforce_fullscreen: true,
    reading_delay_key: 100,
    interference_reading_delay_key: 100,
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
      InterferenceReadingTraining,
      FreeAssociationPre,
      Reading,
      InterferenceReadingTesting,
      FreeAssociationPost,
      QuestionnaireExplanationStoriesBlack,
      QuestionnaireTransportation,
      QuestionnaireComprehension,
      QuestionnaireExperience,
      QuestionnaireExplanationStoriesPurple,
      QuestionnaireTransportationInterference,
      QuestionnaireComprehensionInterference,
      QuestionnaireExperienceInterference,
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
