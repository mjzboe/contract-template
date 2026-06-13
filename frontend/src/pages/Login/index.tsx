import { useState } from "react";
import { Button, Form, Input, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "登录失败";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #F7F5F2 0%, #EDE9E3 50%, #E8E4DF 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative geometric elements */}
      <div
        style={{
          position: "absolute",
          top: "-20%",
          right: "-10%",
          width: "50vw",
          height: "50vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(184,134,11,0.04) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "-30%",
          left: "-15%",
          width: "60vw",
          height: "60vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(184,134,11,0.03) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      {/* Subtle grid pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(0,0,0,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.015) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          width: 420,
          padding: "56px 48px 48px",
          background: "rgba(255,255,255,0.85)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderRadius: 20,
          border: "1px solid rgba(232,228,223,0.6)",
          boxShadow:
            "0 8px 32px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.03)",
          position: "relative",
          zIndex: 1,
          animation: "fadeInScale 0.5s ease-out",
        }}
      >
        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div
            style={{
              fontFamily: "'Cormorant Garamond', Georgia, serif",
              fontSize: 36,
              fontWeight: 600,
              color: "#1A1A1A",
              letterSpacing: "0.04em",
              lineHeight: 1.1,
            }}
          >
            SIGNAPAGE
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#999",
              marginTop: 8,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
            }}
          >
            签字页管理系统
          </div>
          <div
            style={{
              width: 40,
              height: 2,
              background: "#B8860B",
              margin: "16px auto 0",
              borderRadius: 1,
            }}
          />
        </div>

        <Form onFinish={onFinish} size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: "#BFBFBF" }} />}
              placeholder="用户名"
              style={{
                height: 48,
                borderRadius: 10,
                border: "1px solid #E8E4DF",
                background: "rgba(255,255,255,0.6)",
                fontSize: 14,
              }}
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: "#BFBFBF" }} />}
              placeholder="密码"
              style={{
                height: 48,
                borderRadius: 10,
                border: "1px solid #E8E4DF",
                background: "rgba(255,255,255,0.6)",
                fontSize: 14,
              }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 24 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 48,
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 500,
                letterSpacing: "0.06em",
              }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div
          style={{
            color: "#BFBFBF",
            fontSize: 11.5,
            textAlign: "center",
            letterSpacing: "0.03em",
          }}
        >
          默认管理员：admin / admin123
        </div>
      </div>
    </div>
  );
}
