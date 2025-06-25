define(["component/Pages", "component/InterferencePause"], function (
  Pages,
  InterferencePause
) {
  let study;
  let task_pages;
  let task;

  return {
    name: "interference_pause_testing",
    init: function (_study) {
      study = _study;
      task_pages = new Pages();
      task = new InterferencePause();
      task.init(
        study,
        task_pages,
        function () {
          study.next();
        },
        study.config["interference_pause_time"]
      );
      return Promise.all([
        task_pages.init(study, "interference_pause_testing/task.html"),
      ]);
    },
    show: function () {
      task.start_task();
    },
    finish_task: function () {
      task.finish_task();
    },
  };
});
