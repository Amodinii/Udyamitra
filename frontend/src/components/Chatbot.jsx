import { useState } from 'react';
import { useImmer } from 'use-immer';
import api from '@/api';
import ChatMessages from '@/components/ChatMessages';
import ChatInput from '@/components/ChatInput';

function Chatbot() {
  const [messages, setMessages] = useImmer([]);
  const [newMessage, setNewMessage] = useState('');

  const isLoading = messages.length && messages[messages.length - 1].loading;

  function getTimeBasedGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning!';
    if (hour < 18) return 'Good afternoon!';
    return 'Good evening!';
  }

  async function handleFollowUpInput(followUpValue) {
    setNewMessage('');
    const lastMessage = messages[messages.length - 1];
    const info = lastMessage.pendingToolInfo;
    if (!info) return;

    const inputKey = info.required_inputs[info.current_index];
    const updatedInputs = {
      ...info.collected_inputs,
      [inputKey]: followUpValue
    };
    const nextIndex = info.current_index + 1;

    // Add user input and start assistant reply
    setMessages(draft => [
      ...draft,
      { role: 'user', content: followUpValue },
      { role: 'assistant', content: '', loading: true }
    ]);

    if (nextIndex < info.required_inputs.length) {
      const nextInputKey = info.required_inputs[nextIndex];

      // Prompt next required input
      setMessages(draft => {
        draft[draft.length - 1] = {
          role: 'assistant',
          content: `Please provide the ${nextInputKey}.`,
          loading: false,
          pendingToolInfo: {
            ...info,
            current_index: nextIndex,
            collected_inputs: updatedInputs
          }
        };
      });
    } else {
      // All inputs collected, call /run
      try {
        const runResponse = await api.runTool({
          user_query: info.user_query,
          user_inputs: updatedInputs,
          tool_name: info.tool_name,
          server_path: info.server_path,
          server_sources: info.server_sources
        });

        setMessages(draft => {
          draft[draft.length - 1] = {
            role: 'assistant',
            content: runResponse.answer,
            loading: false
          };
        });
      } catch (err) {
        console.error(err);
        setMessages(draft => {
          draft[draft.length - 1].loading = false;
          draft[draft.length - 1].content = 'Something went wrong.';
        });
      }
    }
  }

  async function submitNewMessage() {
    const trimmedMessage = newMessage.trim();
    if (!trimmedMessage || isLoading) return;

    // Show user question
    setMessages(draft => [
      ...draft,
      { role: 'user', content: trimmedMessage },
      { role: 'assistant', content: '', loading: true }
    ]);
    setNewMessage('');

    try {
      const intentResponse = await api.getIntent(trimmedMessage);
      const tool = intentResponse.tool_info[0];

      if (tool.required_inputs.length > 0) {
        const firstInput = tool.required_inputs[0];

        setMessages(draft => {
          draft[draft.length - 1] = {
            role: 'assistant',
            content: `Please provide the ${firstInput}.`,
            loading: false,
            pendingToolInfo: {
              user_query: trimmedMessage,
              tool_name: tool.tool_name,
              required_inputs: tool.required_inputs,
              collected_inputs: {},
              current_index: 0,
              server_path: intentResponse.server_path,
              server_sources: intentResponse.server_sources
            }
          };
        });
      } else {
        // No inputs needed, run immediately
        const runResponse = await api.runTool({
          user_query: trimmedMessage,
          user_inputs: {},
          tool_name: tool.tool_name,
          server_path: intentResponse.server_path,
          server_sources: intentResponse.server_sources
        });

        setMessages(draft => {
          draft[draft.length - 1] = {
            role: 'assistant',
            content: runResponse.answer,
            loading: false
          };
        });
      }
    } catch (err) {
      console.error(err);
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
        draft[draft.length - 1].content = 'Something went wrong.';
      });
    }
  }

  return (
    <div className='relative grow flex flex-col gap-6 pt-6'>
      {messages.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="font-urbanist text-4xl font-semibold text-white text-center px-4">
            Hello there, {getTimeBasedGreeting()}
          </p>
        </div>
      )}

      <ChatMessages messages={messages} isLoading={isLoading} />
      <ChatInput
        newMessage={newMessage}
        isLoading={isLoading}
        setNewMessage={setNewMessage}
        submitNewMessage={() => {
          const last = messages[messages.length - 1];
          if (last?.pendingToolInfo) {
            handleFollowUpInput(newMessage);
          } else {
            submitNewMessage();
          }
        }}
      />
    </div>
  );
}

export default Chatbot;