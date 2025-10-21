# Mem Integration Test Playground

完整的 `mem` 命令行工具集成测试环境。

## 测试概述

本测试套件验证了 mem 工具的核心功能，特别关注 `.memignore` 功能的正确性。

### 核心测试点

✅ **.memignore 默认行为**
- `mem init` 自动创建 `.memignore` 文件
- 默认包含 `.*` 规则（忽略所有隐藏文件）
- `.memignore` 自身被正确追踪

✅ **文件忽略规则**
- 隐藏文件（如 `.hidden_file`, `.env`）不会在 `mem status` 中显示
- 尝试 `mem track` 隐藏文件会被拒绝
- 动态添加新规则（如 `*.log`, `temp/`）立即生效
- 已追踪文件不受新规则影响

✅ **基本命令功能**
- `mem init` - 初始化仓库
- `mem track` - 追踪文件（支持中文、空格、特殊字符文件名）
- `mem status` - 查看状态
- `mem snapshot` - 创建快照
- `mem history` - 查看历史
- `mem show` - 显示提交详情
- `mem rename` - 重命名文件
- `mem amend` - 修改提交信息

## 目录结构

```
test_playground/
├── README.md           # 测试说明文档（本文件）
├── setup.sh            # 创建测试环境
├── cleanup.sh          # 清理测试环境
├── run_tests.sh        # 集成测试脚本
└── sample_project/     # 测试项目（由 setup.sh 创建）
```

## 使用方法

### 1. 设置测试环境

```bash
./setup.sh
```

这会创建一个包含各种文件类型的示例项目：
- 普通文本文件
- 源代码文件（Python）
- 文档文件（Markdown）
- 数据文件（JSON, YAML）
- 隐藏文件（应该被忽略）
- 特殊文件名（中文、空格）

### 2. 运行测试

可以选择自动化测试或手动测试：

**选项 A: 自动化测试**
```bash
./run_tests.sh
```

**选项 B: 手动测试**
```bash
cd sample_project
# 然后按照下面的"手动测试步骤"执行命令
```

### 3. 清理环境

```bash
./cleanup.sh
```

## 手动测试步骤

推荐手动测试以更好地理解每个命令的行为：

```bash
# 进入测试项目
cd sample_project

# 1. 初始化
uv run --directory /path/to/memov mem init --loc .

# 2. 查看 .memignore
cat .memignore

# 3. 查看状态（注意隐藏文件不会显示）
uv run --directory /path/to/memov mem status --loc .

# 4. 追踪文件
uv run --directory /path/to/memov mem track --loc . README.md -p "test" -r "test"

# 5. 修改文件
echo "new content" >> README.md

# 6. 查看修改状态
uv run --directory /path/to/memov mem status --loc .

# 7. 创建快照
uv run --directory /path/to/memov mem snap --loc . -p "snapshot" -r "test"

# 8. 添加新的忽略规则
echo "*.log" >> .memignore

# 9. 创建应该被忽略的文件
echo "log" > app.log

# 10. 查看状态（app.log 不应该显示）
uv run --directory /path/to/memov mem status --loc .

# 11. 查看历史
uv run --directory /path/to/memov mem history --loc .
```

## 测试验证点

在手动测试时，请验证以下行为：

### .memignore 功能
- [ ] `.memignore` 在 `mem init` 时自动创建
- [ ] `.memignore` 包含默认规则 `.*`
- [ ] `.memignore` 自身被追踪（在 history 中可见）
- [ ] 隐藏文件（`.hidden_file`, `.env`）**不显示**在 `mem status` 中
- [ ] 尝试 `mem track .hidden_file` 失败或被忽略
- [ ] 添加新规则后（如 `*.log`），匹配的文件立即从 status 中消失
- [ ] 已追踪的文件即使匹配新规则也继续显示状态

### 文件操作
- [ ] 可以追踪包含中文的文件名
- [ ] 可以追踪包含空格的文件名
- [ ] 可以追踪目录
- [ ] 修改文件后 status 显示为 Modified
- [ ] snapshot 后文件显示为 Clean
- [ ] rename 功能正常工作
- [ ] history 正确记录所有操作

## 测试结果

**日期**: 2025-10-21

**状态**: ✅ 所有核心功能测试通过

**关键发现**:
1. `.memignore` 默认规则(`.*`)正确工作
2. 隐藏文件完全不显示在 status 中（符合预期）
3. 动态添加规则立即生效
4. 所有文件操作命令正常工作
5. 支持特殊字符文件名（中文、空格等）

## 后续改进建议

1. 添加自动化测试断言，验证输出内容
2. 测试更多边缘情况（符号链接、只读文件等）
3. 性能测试（大量文件、大文件）
4. 考虑添加 `jump` 命令的测试
