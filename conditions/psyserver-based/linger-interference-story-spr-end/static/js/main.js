require([
  "module/Study",
  "stage/Welcome",
  "stage/ContentWarning",
  "stage/Consent",
  "stage/Fullscreen",
  "stage/GeneralInstructions",
  "stage/InterferenceGeometryTraining",
  "stage/FreeAssociationPre",
  "stage/Reading",
  "stage/Manipulation",
  "stage/InterferenceReadingTesting",
  "stage/FreeAssociationPost",
  "stage/QuestionnaireManipulationCheck",
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
  "stage/Captcha",
  "stage/Complete",
], function (
  Study,
  Welcome,
  ContentWarning,
  Consent,
  Fullscreen,
  GeneralInstructions,
  InterferenceGeometryTraining,
  FreeAssociationPre,
  Reading,
  Manipulation,
  InterferenceReadingTesting,
  FreeAssociationPost,
  QuestionnaireManipulationCheck,
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
  Captcha,
  Complete
) {
  // configuration
  let _version = "1.0.1";
  let config = {
    study: "linger-interference-story-spr-end",
    version: _version,
    debug: false,
    default_button_timeout: 500,
    time_limit_pre: 180000,
    time_limit_post: 180000,
    code_completion: "CGWO2HA6",
    code_noconsent: "CEH4RWLC",
    code_content_warning_disagree: "CAYTAWD0",
    code_honeypot: "C13F7P5H",
    studytime: 40,
    enforce_fullscreen: true,
    reading_delay_key: 100,
    interference_reading_delay_key: 100,
    conditions: ["separated", "continued", "delayed-continued"],
    interference_geometry_training_image_index: 1,
    interference_geometry_testing_image_indices: [8, 9, 10, 11],
    interference_geometry_time_image: 18000,
    interference_geometry_time_question: 8000,
    interference_geometry_time_pause: 4000,
  };

  // determine debug mode
  let url_params = new URLSearchParams(window.location.search);
  if (url_params.get("mode") == "debug") {
    config["debug"] = true;
    config["default_button_timeout"] = 0;
    config["time_limit_pre"] = 6000;
    config["time_limit_post"] = 6000;
    config["enforce_fullscreen"] = false;
    config["interference_geometry_time_image"] = 2000;
    config["interference_geometry_time_question"] = 2000;
    config["interference_geometry_time_pause"] = 1000;
  }

  // local mode: needed to determine how data is saved
  config["local"] = false;
  if (url_params.has("local")) {
    config["local"] = true;
  }

  // condition
  if (url_params.has("condition")) {
    config["condition"] = url_params.get("condition");
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
      InterferenceGeometryTraining,
      FreeAssociationPre,
      Reading,
      Manipulation,
      InterferenceReadingTesting,
      FreeAssociationPost,
      QuestionnaireManipulationCheck,
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
      Captcha,
      Complete,
    ],
    config
  );
  initialization.then(() => {
    Study.next();
  });
});
