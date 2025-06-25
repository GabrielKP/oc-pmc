define(["component/Pages", "component/FreeAssociation"], function (
  Pages,
  FreeAssociation
) {
  let study;
  let instruct_pages;
  let free_association;

  return {
    name: "free_association_post",
    init: function (_study) {
      study = _study;
      instruct_pages = new Pages();
      free_association = new FreeAssociation();
      return Promise.all([
        instruct_pages.init(
          study,
          [
            "free_association_post/instruct-1.html",
            "free_association_post/instruct-2.html",
            "free_association_post/instruct-3.html",
          ],
          function () {
            free_association.start_task();
          }
        ),
        free_association.init(
          study,
          "free_association_post/task.html",
          function () {
            study.next();
          },
          study.config.time_limit_post
        ),
      ]);
    },
    show: function () {
      // show instructions first
      instruct_pages.next();
    },
  };
});
