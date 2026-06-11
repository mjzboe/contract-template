import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import TemplateManagePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("TemplateManagePage", () => {
  it("renders template list with data from API", async () => {
    renderWithProviders(<TemplateManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试模板")).toBeInTheDocument();
    });
  });

  it("renders upload button", () => {
    renderWithProviders(<TemplateManagePage />);
    expect(screen.getByText("上传模板")).toBeInTheDocument();
  });

  it("renders search input", () => {
    renderWithProviders(<TemplateManagePage />);
    expect(screen.getByPlaceholderText("搜索模板")).toBeInTheDocument();
  });
});
