import { NextRequest, NextResponse } from 'next/server';
import { STRATEGY_TEMPLATES, getStrategyTemplate, STRATEGY_CATEGORIES } from '@/lib/strategyTemplates';

// GET /api/strategies/templates - Get all strategy templates or specific template
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const type = url.searchParams.get('type');

    if (type) {
      // Get specific template
      const template = getStrategyTemplate(type);
      if (!template) {
        return NextResponse.json(
          { error: `Strategy template '${type}' not found` },
          { status: 404 }
        );
      }

      return NextResponse.json({
        template,
        timestamp: new Date().toISOString()
      });
    } else {
      // Get all templates
      return NextResponse.json({
        templates: STRATEGY_TEMPLATES,
        categories: STRATEGY_CATEGORIES,
        total_count: STRATEGY_TEMPLATES.length,
        timestamp: new Date().toISOString()
      });
    }
  } catch (error) {
    console.error('Failed to fetch strategy templates:', error);
    return NextResponse.json(
      { error: 'Failed to fetch strategy templates', details: error.message },
      { status: 500 }
    );
  }
}
