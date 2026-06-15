import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import ProjectManagePage from "./index";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ConfigProvider>
  );
}

describe("ProjectManagePage", () => {
  it("renders project table and search bar", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("搜索项目名称")).toBeInTheDocument();
  });

  it("loads and displays projects from API", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
  });

  it("renders status filter select", () => {
    renderWithProviders(<ProjectManagePage />);
    expect(screen.getByText("全部状态")).toBeInTheDocument();
  });

  it("renders new project button", () => {
    renderWithProviders(<ProjectManagePage />);
    expect(screen.getByText("新建项目")).toBeInTheDocument();
  });

  it("renders action buttons for each project", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    expect(screen.getByText("详情")).toBeInTheDocument();
    expect(screen.getByText("编辑")).toBeInTheDocument();
    expect(screen.getByText("生成")).toBeInTheDocument();
  });

  it("opens detail modal on project name click", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("测试项目"));
    await waitFor(() => {
      expect(screen.getByText("项目详情")).toBeInTheDocument();
    });
  });

  it("opens edit modal on edit button click", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    const editButtons = screen.getAllByText("编辑");
    fireEvent.click(editButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("编辑项目")).toBeInTheDocument();
    });
  });

  it("renders delete button with confirmation", async () => {
    renderWithProviders(<ProjectManagePage />);
    await waitFor(() => {
      expect(screen.getByText("测试项目")).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByText("删除");
    expect(deleteButtons.length).toBeGreaterThan(0);
  });
});
