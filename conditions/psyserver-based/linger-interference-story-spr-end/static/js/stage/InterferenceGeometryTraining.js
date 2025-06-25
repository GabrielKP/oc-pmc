define(["component/Pages", "component/InterferenceGeometry"], function (
  Pages,
  InterferencePause
) {
  let study;
  let instruct_pages;
  let task_pages;
  let task;
  let iteration;
  let mode;

  function _init_start_task() {
    mode = "task";
    task_pages.reset();
    task = new InterferencePause();
    task.init(
      study,
      task_pages,
      (answered_question, correct_answer) => {
        _conditional_next(answered_question, correct_answer);
      },
      study.config["interference_geometry_training_image_index"],
      study.config["interference_geometry_time_image"],
      study.config["interference_geometry_time_question"],
      study.config["interference_geometry_time_pause"],
      iteration
    );
    task.start_task();
  }

  function _conditional_next(correct, correct_answer) {
    if (!correct) {
      iteration += 1;
      final_failed.reset();
      final_failed.next();
      // $("#correct_answer").html(
      //   "The correct answer would have been " + correct_answer + "."
      // );
    } else {
      mode = "finish";
      final_neutral.reset();
      final_neutral.next();
    }
  }

  return {
    name: "interference_geometry_training",
    init: function (_study) {
      study = _study;
      instruct_pages = new Pages();
      task_pages = new Pages();
      final_neutral = new Pages();
      final_failed = new Pages();
      iteration = 0;
      mode = "init";
      return Promise.all([
        instruct_pages.init(
          study,
          [
            "interference_geometry_training/instruct-1.html",
            "interference_geometry_training/instruct-2.html",
            "interference_geometry_training/instruct-3.html",
            "interference_geometry_training/instruct-4.html",
          ],
          () => {
            _init_start_task();
          }
        ),
        task_pages.init(study, "interference_geometry_training/task.html"),
        final_failed.init(
          study,
          "interference_geometry_training/instruct-final_failed.html",
          () => {
            _init_start_task();
          }
        ),
        final_neutral.init(
          study,
          "interference_geometry_training/instruct-final_neutral.html",
          () => {
            study.next();
          }
        ),
      ]);
    },
    show: function () {
      // show instructions first
      mode = "instructions";
      instruct_pages.next();
    },
    finish_task: function (skip = false) {
      if (mode == "instructions") {
        _init_start_task();
      } else {
        task.finish_task(skip);
        study.next();
      }
    },
  };
});
