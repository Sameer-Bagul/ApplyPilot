import { NextResponse } from 'next/server';
import { getCandidateProfile } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const query = (body.query || body.tech || '').trim();

    if (!query) {
      return NextResponse.json({ success: false, error: 'Query or tech stack keyword is required' }, { status: 400 });
    }

    const { profile } = getCandidateProfile();
    const qLower = query.toLowerCase();

    // 1. Check direct match in curated projects
    const projects = profile.projects || [];
    for (const proj of projects) {
      const titleMatch = proj.title?.toLowerCase().includes(qLower);
      const descMatch = proj.shortDescription?.toLowerCase().includes(qLower);
      const techMatch = proj.techStack?.some((t: string) => t.toLowerCase().includes(qLower));

      if (titleMatch || descMatch || techMatch) {
        const story = `In ${proj.title}, I worked extensively with ${query}. ${proj.shortDescription} Specifically, I ${proj.highlights?.[0] || 'engineered core microservices and scalable pipelines'} utilizing ${proj.techStack?.slice(0, 5).join(', ')}, achieving ${proj.metrics || 'production reliability'}.`;
        const quickAnswer = `Yes, I built ${proj.title} utilizing ${query} and production microservice architectures.`;

        return NextResponse.json({
          success: true,
          query,
          matched_project: proj.title,
          is_bridge: false,
          story,
          quick_answer: quickAnswer,
          github_url: proj.githubUrl || '',
          metrics: proj.metrics || '',
        });
      }
    }

    // 2. Check work experiences
    const experiences = profile.experiences || [];
    for (const exp of experiences) {
      const compMatch = exp.company?.toLowerCase().includes(qLower);
      const roleMatch = exp.role?.toLowerCase().includes(qLower);
      const techMatch = exp.skills?.some((s: string) => s.toLowerCase().includes(qLower));
      const highlightMatch = exp.highlights?.some((h: string) => h.toLowerCase().includes(qLower));

      if (compMatch || roleMatch || techMatch || highlightMatch) {
        const story = `During my time as ${exp.role} at ${exp.company}, I utilized ${query} to solve key operational requirements. ${exp.summary} Specifically, I ${exp.highlights?.[0] || 'built robust production features'} in a stack spanning ${exp.skills?.slice(0, 5).join(', ')}.`;
        const quickAnswer = `Yes, 2+ years of production experience utilizing ${query} during my work at ${exp.company}.`;

        return NextResponse.json({
          success: true,
          query,
          matched_project: `${exp.role} at ${exp.company}`,
          is_bridge: false,
          story,
          quick_answer: quickAnswer,
          metrics: `${exp.company} (${exp.start_date} – ${exp.end_date})`,
        });
      }
    }

    // 3. Check predefined story matrix rules
    const rules = profile.story_matrix?.rules || [];
    for (const r of rules) {
      if (r.tech.toLowerCase().includes(qLower) || qLower.includes(r.tech.toLowerCase().split(' ')[0])) {
        return NextResponse.json({
          success: true,
          query,
          matched_project: `Bridge Architecture: ${r.bridge_domain}`,
          is_bridge: true,
          story: r.story,
          quick_answer: `Yes, experienced with ${query} in ${r.bridge_domain.toLowerCase()} and production workflows.`,
        });
      }
    }

    // 4. Synthesize professional engineering bridge story for any novel tech XYZ
    const capitalizedQuery = query.charAt(0).toUpperCase() + query.slice(1);
    const synthesizedStory = `Yes, I have worked with ${capitalizedQuery} in the context of distributed systems, high-concurrency event routing, and agent infrastructure. In our service architectures, I integrated ${capitalizedQuery} to handle asynchronous workload isolation and resilient error recovery, interfacing directly with Docker containers, FastAPI endpoints, and Next.js interfaces. My strong foundation in systems programming and full-stack architecture allows me to deploy, debug, and scale ${capitalizedQuery} pipelines with minimal ramp-up time.`;
    const quickAnswer = `Yes, experienced utilizing ${capitalizedQuery} across distributed agent workflows and backend microservices.`;

    return NextResponse.json({
      success: true,
      query,
      matched_project: `Synthesized Bridge: ${capitalizedQuery} Systems Engineering`,
      is_bridge: true,
      story: synthesizedStory,
      quick_answer: quickAnswer,
    });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
