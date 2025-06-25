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
  "stage/InterferenceGeometryTesting",
  "stage/FreeAssociationPost",
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
  InterferenceGeometryTraining,
  FreeAssociationPre,
  Reading,
  InterferenceGeometryTesting,
  FreeAssociationPost,
  QuestionnaireTransportation,
  QuestionnaireComprehension,
  QuestionnaireExperience,
  QuestionnaireDemographics,
  QuestionnaireOpen,
  Complete
) {
  // configuration
  let _version = "1.0.2";
  let config = {
    study: "linger-interference-geometry",
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
    interference_geometry_training_image_index: 1,
    interference_geometry_testing_image_index: 8,
    interference_geometry_time_image: 18000,
    interference_geometry_time_question: 8000,
    interference_geometry_pause: 4000,
  };

  // determine debug mode
  // The names refer to geometry, but should be treated as situation.
  let url_params = new URLSearchParams(window.location.search);
  if (url_params.get("mode") == "debug") {
    config["debug"] = true;
    config["default_button_timeout"] = 0;
    config["time_limit_pre"] = 6000;
    config["time_limit_post"] = 6000;
    config["enforce_fullscreen"] = false;
    config["interference_geometry_time_image"] = 6000;
    config["interference_geometry_time_question2"] = 6000;
    config["interference_geometry_time_pause"] = 1000;
    config["interference_geometry_min_training_sessions"] = 3;
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
      InterferenceGeometryTraining,
      FreeAssociationPre,
      Reading,
      InterferenceGeometryTesting,
      FreeAssociationPost,
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
