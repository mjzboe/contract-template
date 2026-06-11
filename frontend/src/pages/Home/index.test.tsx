import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import HomePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("HomePage", () => {
  it("renders statistic cards", async () => {
    renderWithProviders(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("模板总数")).toBeInTheDocument();
      expect(screen.getByText("项目总数")).toBeInTheDocument();
      expect(screen.getByText("已生成签字页")).toBeInTheDocument();
    });
  });

  it("renders recent projects", async () => {
    renderWithProviders(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("最近项目")).toBeInTheDocument();
    });
  });

  it("renders action buttons", () => {
    renderWithProviders(<HomePage />);
    expect(screen.getByText("创建项目")).toBeInTheDocument();
    expect(screen.getByText("管理模板")).toBeInTheDocument();
  });
});
