define([], function () {
  class _InterferencePause {
    total_pause_time;
    mode;
    pages;
    pagenames;
    finish_func;
    study;
    task_start_time;
    time_pressed;
    start_time_pressed;
    time_unpressed;
    start_time_unpressed;
    unpressed;
    initial_press;
    iteration;

    constructor() {
      // bind all the functions
      this.keydown_handler = this.keydown_handler.bind(this);
      this.keyup_handler = this.keyup_handler.bind(this);
      // this.timer_fnc = this.timer_fnc.bind(this);
      this.finish_task = this.finish_task.bind(this);
      this.start_task = this.start_task.bind(this);
    }

    init(study, page_object, finish_func, pause_time, iteration = 0) {
      this.study = study;
      this.pages = page_object;
      this.finish_func = finish_func;
      this.total_pause_time = pause_time;
      this.update_interval = 1000;
      this.current_time = 0;
      this.time_pressed = 0;
      this.time_unpressed = 0;
      this.unpressed = true;
      this.iteration = iteration;
      this.initial_press = true;
    }

    finish_task() {
      // unbind
      $("body").off();
      // task_time - (time_unpressed + total_pause_time) = time_unpressed at start
      let task_time = new Date().getTime() - this.task_start_time;
      this.study.data.record_trialdata({
        status: "task_end",
        task: "interference_pause",
        time_unpressed: this.time_unpressed,
        time_total_pause: this.total_pause_time,
        time_unpressed_start:
          task_time - (this.total_pause_time + this.time_unpressed),
        task_time: task_time,
        iteration: this.iteration,
      });
      $("body").unbind("keydown", this.response_handler);
      this.finish_func(this.time_unpressed);
      $("body").css({ border: "", height: "" });
      $("html").css({ height: "" });
    }

    keydown_handler(key) {
      key.preventDefault();
      // Need bool as holding down spacebar generates multiple events
      if (key.keyCode == 32 && this.unpressed) {
        this.unpressed = false;

        // visuals
        $("#spacebar-warning").css("opacity", 0);
        $("#pb").removeClass("bg-danger");
        $("#pb").addClass("bg-success");
        $("#pb").animate(
          { width: "100%" },
          this.total_pause_time - this.time_pressed,
          "linear",
          () => {
            this.finish_task();
          }
        );

        // pressed/unpressed time tracking
        if (this.initial_press) this.initial_press = false;
        else
          this.time_unpressed +=
            new Date().getTime() - this.start_time_unpressed;
        this.start_time_pressed = new Date().getTime();
      }
    }

    keyup_handler(key) {
      key.preventDefault();
      if (key.keyCode == 32 && !this.unpressed) {
        this.unpressed = true;

        // visuals
        $("#spacebar-warning").html("<h2>Do not release the spacebar!</h2>");
        $("#spacebar-warning").css("opacity", 1);
        $("#pb").removeClass("bg-success");
        $("#pb").addClass("bg-danger");
        $("#pb").stop();

        // track time
        this.time_pressed += new Date().getTime() - this.start_time_pressed;
        this.start_time_unpressed = new Date().getTime();
      }
    }

    start_task() {
      this.pages.next();
      // show blue border
      $("body").css({ border: "40px solid lightblue", height: "100%" });
      $("html").css({ height: "100%" });

      // beginning of pause
      this.study.data.record_trialdata({
        status: "task_begin",
        task: "interference_pause",
        iteration: this.iteration,
      });
      this.task_start_time = new Date().getTime();

      // register event listener
      $("body").focus().keydown(this.keydown_handler);
      $("body").focus().keyup(this.keyup_handler);
    }
  }

  return _InterferencePause;
});
