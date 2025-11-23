import type { ThemeConfig } from 'antd'

/**
 * 企业级主题配置
 * 设计原则：简洁、专业、高信息密度
 */
const theme: ThemeConfig = {
  token: {
    // ===== 颜色系统 =====
    colorPrimary: '#0052D9', // 沉稳蓝（主色）
    colorSuccess: '#00A870', // 成功绿
    colorWarning: '#FF8800', // 警告橙
    colorError: '#D54941', // 错误红
    colorInfo: '#0052D9', // 信息色（同主色）

    // 文本颜色
    colorText: '#252B3A', // 主文本
    colorTextSecondary: '#8F959E', // 次要文本
    colorTextTertiary: '#BBBFC4', // 三级文本
    colorTextQuaternary: '#E5E6EB', // 四级文本（禁用）

    // 背景颜色
    colorBgLayout: '#F5F7FA', // 布局背景（浅灰）
    colorBgContainer: '#FFFFFF', // 容器背景（白色）
    colorBgElevated: '#FFFFFF', // 浮层背景

    // 边框颜色
    colorBorder: '#E5E6EB', // 默认边框
    colorBorderSecondary: '#F0F0F0', // 次要边框

    // ===== 形状与尺寸 =====
    borderRadius: 4, // 默认圆角（小组件）
    borderRadiusLG: 6, // 大圆角（大组件）
    borderRadiusSM: 2, // 小圆角（按钮等）

    // ===== 间距系统 =====
    paddingXS: 8,
    paddingSM: 12,
    padding: 16,
    paddingMD: 20,
    paddingLG: 24,
    paddingXL: 32,

    marginXS: 8,
    marginSM: 12,
    margin: 16,
    marginMD: 20,
    marginLG: 24,
    marginXL: 32,

    // ===== 字体系统 =====
    fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
    fontSize: 14, // 基础字号
    fontSizeLG: 16, // 大字号
    fontSizeSM: 12, // 小字号
    fontSizeHeading1: 38,
    fontSizeHeading2: 30,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,

    // ===== 阴影系统（轻量化）=====
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
    boxShadowSecondary: '0 2px 8px 0 rgba(0, 0, 0, 0.05)',

    // ===== 其他 =====
    lineHeight: 1.5715,
    controlHeight: 32, // 控件高度
    controlHeightLG: 40, // 大控件高度
    controlHeightSM: 24, // 小控件高度
  },

  components: {
    // 布局组件
    Layout: {
      headerBg: '#FFFFFF',
      headerHeight: 56,
      headerPadding: '0 24px',
      siderBg: '#FFFFFF',
      bodyBg: '#F5F7FA',
      triggerBg: '#F5F7FA',
    },

    // 菜单组件
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#F0F5FF',
      itemSelectedColor: '#0052D9',
      itemHoverBg: '#F5F7FA',
      itemHoverColor: '#252B3A',
      itemHeight: 40,
      itemMarginInline: 4,
      itemBorderRadius: 4,
    },

    // 卡片组件
    Card: {
      boxShadow: 'none',
      borderRadius: 4,
      paddingLG: 24,
    },

    // 按钮组件
    Button: {
      borderRadius: 4,
      controlHeight: 32,
      controlHeightLG: 40,
      controlHeightSM: 24,
      primaryShadow: 'none',
    },

    // 表格组件
    Table: {
      headerBg: '#FAFAFA',
      headerColor: '#8F959E',
      borderColor: '#F0F0F0',
      rowHoverBg: '#F5F7FA',
    },

    // 统计数值组件
    Statistic: {
      titleFontSize: 14,
      contentFontSize: 24,
    },

    // 面包屑组件
    Breadcrumb: {
      itemColor: '#8F959E',
      linkColor: '#8F959E',
      linkHoverColor: '#0052D9',
      lastItemColor: '#252B3A',
      fontSize: 14,
    },
  },
}

export default theme
