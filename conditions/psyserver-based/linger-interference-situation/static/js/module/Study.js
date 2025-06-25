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

    get_condition() {
      if (this.config["conditions"].length == 0) return Promise.resolve();
      return $.ajax({ url: "get_count", type: "GET" })
        .done((data) => {
          let condition_idx = data["count"] % this.config["conditions"].length;
          let condition = this.config["conditions"][condition_idx];

          this.config["condition"] = condition;
          this.config["condition_idx"] = condition_idx;
          this.data.record_trialdata({
            condition: condition,
            condition_idx: condition_idx,
            count: data["count"],
          });
          console.log("Condition: " + condition);
        })
        .catch(() => {
          console.log("Failed to determine condition. Setting it to 0.");
          let condition_idx = 0;
          let condition = this.config["conditions"][condition_idx];

          this.config["condition"] = condition;
          this.config["condition_idx"] = condition_idx;
          this.data.record_trialdata({
            condition: condition,
            condition_idx: condition_idx,
            count: null,
          });
          console.log("Condition: " + condition);
        });
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

      // let condition_promise = this.get_condition();

      return Promise.all(
        $.map(uninit_stages, (stage, indx) => {
          return stage.init(this).then(() => {
            this.stages[indx] = stage;
          });
        }).concat(this.get_condition())
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
