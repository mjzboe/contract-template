import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import ContractGeneratePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("ContractGeneratePage", () => {
  it("renders steps component", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getAllByText("创建项目").length).toBeGreaterThan(0);
    expect(screen.getByText("填写变量")).toBeInTheDocument();
    expect(screen.getByText("生成下载")).toBeInTheDocument();
  });

  it("renders project name input in step 1", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getByPlaceholderText("输入项目名称，如：XX公司IPO签字页")).toBeInTheDocument();
  });

  it("renders template table in step 1", async () => {
    renderWithProviders(<ContractGeneratePage />);
    await waitFor(() => {
      expect(screen.getByText("测试模板")).toBeInTheDocument();
    });
  });

  it("renders next step button", () => {
    renderWithProviders(<ContractGeneratePage />);
    expect(screen.getByText(/下一步/)).toBeInTheDocument();
  });
});
