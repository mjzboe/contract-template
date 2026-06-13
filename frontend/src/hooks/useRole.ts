import { useAuthStore } from "../stores/authStore";

const ROLE_LABELS: Record<string, string> = {
  super_admin: "超级管理员",
  template_admin: "模板管理员",
  approver: "审批人",
  user: "普通用户",
};

export function useRole() {
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? "user";

  return {
    role,
    roleLabel: ROLE_LABELS[role] || role,
    isSuperAdmin: role === "super_admin",
    isTemplateAdmin: role === "template_admin",
    isApprover: role === "approver",
    isUser: role === "user",
    hasRole: (...roles: string[]) => roles.includes(role),
  };
}
