define(["component/Pages", "component/InterferenceTom"], function (
  Pages,
  InterferencePause
) {
  let study;
  let task_pages;
  let task;

  function _init_start_task() {
    task = new InterferencePause();
    let testing_passage_index =
      study.config["interference_tom_testing_passage_indices"][
        study.config["condition_idx"]
      ];
    task.init(
      study,
      task_pages,
      () => {
        study.next();
      },
      [testing_passage_index],
      study.config["interference_tom_time_passage"],
      study.config["interference_tom_time_question"],
      study.config["interference_tom_time_pause"],
      0
    );
    task.start_task();
  }

  return {
    name: "interference_tom_testing",
    init: function (_study) {
      study = _study;
      task_pages = new Pages();
      return Promise.all([
        task_pages.init(study, "interference_tom_testing/task.html"),
      ]);
    },
    show: function () {
      _init_start_task();
    },
    finish_task: function (skip = false) {
      task.finish_task(skip);
    },
  };
});
