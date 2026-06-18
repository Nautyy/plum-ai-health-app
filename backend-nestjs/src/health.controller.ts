import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  health() {
    const langGraphUrl = (process.env.LANGGRAPH_BASE_URL || 'http://127.0.0.1:2024').replace(/\/$/, '');
    return {
      status: 'ok',
      langgraph_base_url: langGraphUrl,
      graph_id: process.env.LANGGRAPH_GRAPH_ID || 'claims_adjudication',
    };
  }
}
