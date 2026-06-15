"""演示数据种子脚本 — 创建完整业务场景数据

用法: cd backend && python -m scripts.seed_demo
前置: 确保后端服务运行在 localhost:8000，且数据库为空或可覆盖
"""

import asyncio
import os

import httpx

BASE = "http://localhost:8000/api/v1"
SAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "samples")


async def seed():
    async with httpx.AsyncClient(timeout=30) as raw_client:
        # 1. 确保 admin 用户存在
        r = await raw_client.post(f"{BASE}/auth/init-admin")
        admin_data = r.json()
        print(f"[1/7] admin 用户: {admin_data['username']} ({admin_data['role']})")

        # 2. 登录获取 token
        r = await raw_client.post(
            f"{BASE}/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = r.json()["access_token"]
        client = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30)

        # 3. 创建分类
        r = await client.post(f"{BASE}/categories", json={"name": "IPO签字页"})
        cat_id = r.json()["id"]
        print(f"[2/7] 分类创建: IPO签字页 ({cat_id})")

        # 4. 上传3个模板
        template_ids = []
        for filename in [
            "签字页模板_股东会决议.docx",
            "签字页模板_董事会决议.docx",
            "签字页模板_律师见证函.docx",
        ]:
            path = os.path.join(SAMPLES, filename)
            with open(path, "rb") as f:
                r = await client.post(
                    f"{BASE}/templates",
                    data={
                        "name": filename.replace(".docx", ""),
                        "tags": "[]",
                        "category_id": str(cat_id),
                    },
                    files={"file": (filename, f, "application/octet-stream")},
                )
            data = r.json()
            tid = data["template"]["id"]
            template_ids.append(tid)
            var_names = [v["name"] for v in data["variables"]]
            print(f"[3/7] 模板上传: {filename} — {len(data['variables'])} 个变量 ({', '.join(var_names)})")

        # 5. 创建项目
        r = await client.post(
            f"{BASE}/projects",
            json={"name": "XX科技IPO签字页项目", "template_ids": template_ids},
        )
        project_id = r.json()["id"]
        print(f"[4/7] 项目创建: XX科技IPO签字页项目 ({project_id})")

        # 6. 获取去重变量
        r = await client.get(f"{BASE}/projects/{project_id}/deduplicated-variables")
        dedup = r.json()
        print(
            f"[5/7] 变量去重: {dedup['total_variables_before_dedup']} → "
            f"{dedup['total_variables_after_dedup']} "
            f"(减少 {dedup['total_variables_before_dedup'] - dedup['total_variables_after_dedup']} 个重复)"
        )
        shared = {k: v for k, v in dedup["variable_sources"].items() if len(v) > 1}
        if shared:
            print(f"       共享变量: {', '.join(shared.keys())}")

        # 7. 生成3份合同
        var_values = {
            "公司名称": "XX科技股份有限公司",
            "法定代表人": "张三",
            "日期": "2024年12月31日",
            "住所": "北京市海淀区中关村大街1号",
            "注册资本": "人民币壹亿元整",
            "统一社会信用代码": "91110108MA01ABCDEF",
            "董事长": "李四",
            "董事会秘书": "王五",
            "见证律师": "赵六",
            "律师事务所": "北京XX律师事务所",
        }
        for tid in template_ids:
            r = await client.post(
                f"{BASE}/contracts",
                json={
                    "title": "XX科技IPO - 签字页",
                    "template_id": tid,
                    "variables": var_values,
                    "project_id": project_id,
                },
            )
            print(f"[6/7] 合同生成: {r.json()['title']} — {r.status_code}")

        # 8. 创建演示用户
        r = await client.post(
            f"{BASE}/auth/register",
            json={
                "username": "demo_user",
                "email": "demo@test.com",
                "password": "demo123",
                "role": "user",
            },
        )
        print(f"[7/7] 演示用户: demo_user / demo123 — {r.status_code}")

    print("\n=== 演示数据创建完成 ===")
    print("管理员: admin / admin123 (super_admin)")
    print("演示用户: demo_user / demo123 (user)")


if __name__ == "__main__":
    asyncio.run(seed())
