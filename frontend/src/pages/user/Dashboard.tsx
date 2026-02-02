import { Layout, Card, Button, Empty } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import './dashboard.css'

const { Header, Content } = Layout

function Dashboard() {
  return (
    <Layout className="dashboard-layout">
      <Header className="dashboard-header">
        <div className="header-left">
          <h1>小说改编剧本系统</h1>
        </div>
        <div className="header-right">
          <span>用户名</span>
        </div>
      </Header>

      <Content className="dashboard-content">
        <div className="content-header">
          <h2>我的项目</h2>
          <Button type="primary" icon={<PlusOutlined />}>
            新建项目
          </Button>
        </div>

        <div className="project-grid">
          <Empty description="暂无项目，点击新建项目开始" />
        </div>
      </Content>
    </Layout>
  )
}

export default Dashboard
