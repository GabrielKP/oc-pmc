define(["module/Data"], function (Data) {
  class _Study {
    stage_index;
    current_stage;
    stages;
    config;
    data;
    stage_time_start;

    constructor() {
      this.next = this.next.bind(this);
      this.current_stage_name = this.current_stage_name.bind(this);
    }

    init(uninit_stages, config) {
      this.current_stage = null;
      this.stage_index = 0;
      this.stages = Array(uninit_stages.length);
      this.config = config;

      // init the data module
      this.data = Data;
      this.data.init(this);
      this.stage_time_start = new Date().getTime();
      this.data.record_trialdata({ status: "stage_begin" }); // log init stage begin for consistency

      return Promise.all(
        $.map(uninit_stages, (stage, indx) => {
          return stage.init(this).then(() => {
            this.stages[indx] = stage;
          });
        })
      );
    }

    next() {
      this.data.record_trialdata({
        status: "stage_end",
        stage_time: new Date().getTime() - this.stage_time_start,
      });
      if (this.stage_index < this.stages.length) {
        this.current_stage = this.stages[this.stage_index];
        this.current_stage.show();
        this.stage_index += 1;

        this.stage_time_start = new Date().getTime();
        this.data.record_trialdata({
          status: "stage_begin",
        });
        return true;
      } else {
        console.log("Last stage");
        // save data
        return false;
      }
    }

    current_stage_name() {
      if (this.current_stage == null) {
        return "initializing";
      }
      return this.current_stage.name;
    }

    fullscreen_enforcer() {
      if (document.fullscreenElement) {
        $("#container-fullscreen-warning").hide();
        $("#content").show();
      } else {
        $("#container-fullscreen-warning").show();
        $("#content").hide();
      }
    }
  }

  return new _Study();
});
