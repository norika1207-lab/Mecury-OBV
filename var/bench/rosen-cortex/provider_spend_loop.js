import Anthropic from '@anthropic-ai/sdk';
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
setInterval(async () => {
  await client.messages.create({ model: 'claude-3-5-sonnet-latest', max_tokens: 4096, messages: [] });
}, 1000);
