import 'dotenv/config';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { json, urlencoded } from 'express';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { bodyParser: false });
  const corsRaw = process.env.CORS_ORIGINS || 'http://localhost:3000';
  const corsOrigins =
    corsRaw.trim() === '*'
      ? true
      : corsRaw.split(',').map((o) => o.trim()).filter(Boolean);

  app.use(json({ limit: '50mb' }));
  app.use(urlencoded({ extended: true, limit: '50mb' }));

  app.enableCors({ origin: corsOrigins, credentials: true });
  app.setGlobalPrefix('api/v1');
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));

  const port = process.env.PORT || 8000;
  const langGraphUrl = (process.env.LANGGRAPH_BASE_URL || 'http://127.0.0.1:2024').replace(/\/$/, '');
  await app.listen(port);
  console.log(`Claims BFF listening on port ${port}`);
  console.log(`LangGraph: ${langGraphUrl} (graph: ${process.env.LANGGRAPH_GRAPH_ID || 'claims_adjudication'})`);
}

bootstrap();
