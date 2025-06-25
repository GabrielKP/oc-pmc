define(function () {
  class _Data {
    study;
    trialdata;
    eventdata;
    participantID;
    study_id;
    session_id;
    off_focus_time_start;
    off_fullscreen_time_start;

    constructor() {
      this.record_trialdata = this.record_trialdata.bind(this);
      this.record_eventdata = this.record_eventdata.bind(this);
      this.make_datapoint = this.make_datapoint.bind(this);
      this.save = this.save.bind(this);
    }

    init(study) {
      this.study = study;

      let urlParams = new URLSearchParams(window.location.search);
      this.participantID = urlParams.get("PROLIFIC_PID");
      if (this.study.config["debug"]) {
        console.debug("DEBUG: Setting study_id to version number.");
        this.study_id = this.study.config["version"];
      } else {
        this.study_id = urlParams.get("STUDY_ID");
      }
      this.session_id = urlParams.get("SESSION_ID");

      this.off_focus_time_start = null;
      this.off_fullscreen_time_start = null;

      this.trialdata = [];
      this.eventdata = [];

      // bind the event listeners
      $(window).on("resize", () => {
        this.record_eventdata("window_resize", {
          width: $(window).width(),
          height: $(window).height(),
        });
      });
      $(window).on("focus", () => {
        let submit_data = { off_focus_time: null };
        if (this.off_focus_time_start != null) {
          submit_data["off_focus_time"] =
            new Date().getTime() - this.off_focus_time_start;
        }
        this.record_eventdata("window_focus_on", submit_data);
      });
      $(window).on("blur", () => {
        this.record_eventdata("window_focus_out", {});
        // start a timer
        this.off_focus_time_start = new Date().getTime();
      });
      document.documentElement.addEventListener("fullscreenchange", () => {
        if (document.fullscreenElement) {
          let submit_data = { off_fullscreen_time: null };
          if (this.off_fullscreen_time_start != null) {
            submit_data["off_fullscreen_time"] =
              new Date().getTime() - this.off_fullscreen_time_start;
          }
          this.record_eventdata("fullscreen_on", submit_data);
        } else {
          this.record_eventdata("fullscreen_off", {});
          this.off_fullscreen_time_start = new Date().getTime();
        }
      });

      this.record_eventdata("initialized", {});
      $(window).triggerHandler("resize");

      return Promise.resolve();
    }

    make_datapoint() {
      let datapoint = {};
      datapoint["participantID"] = this.participantID;
      datapoint["study_id"] = this.study_id;
      datapoint["session_id"] = this.session_id;
      datapoint["stage"] = this.study.current_stage_name();
      datapoint["timestamp"] = new Date().getTime();
      return datapoint;
    }

    record_trialdata(data) {
      let trialdatapoint = this.make_datapoint();
      trialdatapoint["trial_index"] = this.trialdata.length;
      trialdatapoint["data"] = data;
      this.trialdata.push(trialdatapoint);
      if (this.study.config["debug"]) {
        console.debug("trialdata: " + JSON.stringify(trialdatapoint));
      }
    }

    record_eventdata(event_type, data) {
      let eventdatapoint = this.make_datapoint();
      eventdatapoint["event_index"] = this.eventdata.length;
      eventdatapoint["event_type"] = event_type;
      eventdatapoint["data"] = data;
      this.eventdata.push(eventdatapoint);
      if (this.study.config["debug"]) {
        console.debug("eventdata: " + JSON.stringify(eventdatapoint));
      }
    }

    save(download = false) {
      let data = {
        participantID: this.participantID,
        study_id: this.study_id,
        session_id: this.session_id,
        version: this.study.config["version"],
        config: this.study.config,
        trialdata: this.trialdata,
        eventdata: this.eventdata,
      };
      if (this.study.config["local"] || download) {
        // download the data
        let a = document.createElement("a");
        let file = new Blob([JSON.stringify(data, null, 2)], {
          type: "text/json",
        });
        a.href = URL.createObjectURL(file);
        a.download = "studydata.json";
        a.click();
        return Promise.resolve();
      } else {
        // send data to server
        return $.ajax({
          url: "save",
          type: "POST",
          data: JSON.stringify(data),
          contentType: "application/json",
          success: () => {
            console.log("Saving successful");
            // success function
          },
        });
      }
    }
  }

  return new _Data();
});
