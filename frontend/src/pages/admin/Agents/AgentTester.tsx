import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, Button, message, Spin, Alert, Timeline } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import MonacoEditor from '@monaco-editor/react';

interface Agent {
  id: string;
  name: string;
  display_name: string;
  description: string;
  workflow: any;
}

const AgentTester: React.FC = () => {
  const navigate = useNavigate();
  const { agentId } = useParams<{ agentId: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [contextData, setContextData] = useState('{}');
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  useEffect(() => {
    loadAgent();
  }, [agentId]);

  const loadAgent = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/simple-agents/${agentId}`);
      setAgent(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setResults(null);
    setError(null);
    setExecutionTime(null);

    try {
      const context = JSON.parse(contextData);
      const response = await axios.post(`/api/v1/simple-agents/${agentId}/execute`, {
        context,
      });

      if (response.data.success) {
        setResults(response.data.results);
        setExecutionTime(response.data.execution_time);
        message.success('执行成功');
      } else {
        setError(response.data.error);
        message.error('执行失败');
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || error.message);
      message.error('执行失败');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="p-6">
        <Alert message="Agent 不存在" type="error" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">{agent.display_name}</h1>
            <p className="text-slate-500">{agent.description}</p>
          </div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/admin/agents')}
          >
            返回
          </Button>
        </div>

        {/* 工作流预览 */}
        <div className="mb-4">
          <h3 className="font-semibold mb-2">工作流步骤</h3>
          <Timeline>
            {agent.workflow.steps?.map((step: any, index: number) => (
              <Timeline.Item key={step.id}>
                <div>
                  <span className="font-medium">{step.id}</span>: {step.skill}
                  {results && results[step.output_key] && (
                    <CheckCircleOutlined className="ml-2 text-green-500" />
                  )}
                </div>
              </Timeline.Item>
            ))}
          </Timeline>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* 输入区域 */}
          <div>
            <div className="mb-2 flex justify-between items-center">
              <h3 className="font-semibold">输入上下文 (JSON)</h3>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleTest}
                loading={testing}
              >
                执行测试
              </Button>
            </div>
            <div className="border rounded">
              <MonacoEditor
                height="400px"
                language="json"
                value={contextData}
                onChange={(value) => setContextData(value || '{}')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
              />
            </div>
          </div>

          {/* 输出区域 */}
          <div>
            <div className="mb-2 flex justify-between items-center">
              <h3 className="font-semibold">执行结果</h3>
              {executionTime !== null && (
                <span className="text-sm text-slate-500">
                  耗时: {executionTime.toFixed(2)}s
                </span>
              )}
            </div>

            {error ? (
              <Alert
                message="执行失败"
                description={error}
                type="error"
                showIcon
              />
            ) : results ? (
              <div className="border rounded">
                <MonacoEditor
                  height="400px"
                  language="json"
                  value={JSON.stringify(results, null, 2)}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                  }}
                />
              </div>
            ) : (
              <div className="border rounded p-4 h-[400px] flex items-center justify-center text-slate-400">
                点击"执行测试"查看结果
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AgentTester;
