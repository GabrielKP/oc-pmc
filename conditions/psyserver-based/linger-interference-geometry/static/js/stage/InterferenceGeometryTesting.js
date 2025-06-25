define(["component/Pages", "component/InterferenceGeometry"], function (
  Pages,
  InterferenceGeometry
) {
  let study;
  let task_pages;
  let task;

  function _init_start_task() {
    task = new InterferenceGeometry();
    task.init(
      study,
      task_pages,
      () => {
        study.next();
      },
      study.config["interference_geometry_testing_image_index"],
      study.config["interference_geometry_time_image"],
      study.config["interference_geometry_time_question"],
      study.config["interference_geometry_time_pause"],
      0
    );
    task.start_task();
  }

  return {
    name: "interference_geometry_testing",
    init: function (_study) {
      study = _study;
      task_pages = new Pages();
      return Promise.all([
        task_pages.init(study, "interference_geometry_testing/task.html"),
      ]);
    },
    show: function () {
      _init_start_task();
    },
    finish_task: function (skip = false) {
      task.finish_task(skip);
      study.next();
    },
  };
});
