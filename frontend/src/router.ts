import { createRouter, createWebHistory } from "vue-router";
import LoginView from "./views/LoginView.vue";
import DashboardView from "./views/DashboardView.vue";
import CompetitorsView from "./views/CompetitorsView.vue";
import ActivitiesView from "./views/ActivitiesView.vue";
import AlertsView from "./views/AlertsView.vue";
import NotificationsView from "./views/NotificationsView.vue";
import ExtensionView from "./views/ExtensionView.vue";
import SystemUsersView from "./views/SystemUsersView.vue";
import AuditLogsView from "./views/AuditLogsView.vue";
import ProfileView from "./views/ProfileView.vue";
import { getUserRole, isAuthenticated } from "./auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/login" },
    { path: "/login", component: LoginView },
    { path: "/dashboard", component: DashboardView },
    { path: "/competitors", component: CompetitorsView },
    { path: "/activities", component: ActivitiesView },
    { path: "/alerts", component: AlertsView },
    { path: "/notifications", component: NotificationsView },
    { path: "/extension", component: ExtensionView },
    { path: "/profile", component: ProfileView },
    { path: "/system/users", component: SystemUsersView, meta: { role: "admin" } },
    { path: "/system/audit-logs", component: AuditLogsView, meta: { role: "admin" } },
  ],
});

router.beforeEach((to) => {
  const authed = isAuthenticated();
  const role = getUserRole();
  if (to.path !== "/login" && !authed) {
    return "/login";
  }
  if (to.path === "/login" && authed) {
    return "/dashboard";
  }
  if (to.meta.role === "admin" && role !== "admin") {
    return "/dashboard";
  }
  return true;
});

export default router;
