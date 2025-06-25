define(["component/Pages", "component/FreeAssociation"], function (
  Pages,
  FreeAssociation
) {
  let study;
  let instruct_pages;
  let free_association;

  return {
    name: "free_association_pre",
    init: function (_study) {
      study = _study;
      instruct_pages = new Pages();
      free_association = new FreeAssociation();
      return Promise.all([
        instruct_pages.init(
          study,
          [
            "free_association_pre/instruct-1.html",
            "free_association_pre/instruct-2.html",
            "free_association_pre/instruct-3.html",
          ],
          function () {
            free_association.start_task();
          }
        ),
        free_association.init(
          study,
          "free_association_pre/task.html",
          function () {
            study.next();
          },
          study.config.time_limit_pre
        ),
      ]);
    },
    show: function () {
      // show instructions first
      instruct_pages.next();
    },
    finish_task: function () {
      free_association.finish_task();
    },
  };
});
