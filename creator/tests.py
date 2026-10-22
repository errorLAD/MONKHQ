import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Role
from workspaces.models import Workspace
from creator.models import (
    CreatorProfile, CreatorVoiceProfile, VoiceSample,
    AIScript, ScriptVersion, DiscoveredVideo, SavedInspiration, VideoAnalysis,
    SavedTrendingTopic, ContentIdea, ContentCalendarEntry, InspirationItem,
    PerformanceCoachReport
)
from social.models import SocialAccount, MetaToken
from creator.services.ai_growth_service import AIGrowthService
from creator.services.viral_discovery_service import BreakoutScoringEngine, ViralDiscoveryService
from creator.services.performance_coach_service import PerformanceCoachService
from ai_engine.models import AITokenUsage

class CreatorGrowthStudioTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Creator 1
        self.creator1 = User.objects.create_user(username='growth_creator_1', password='password123', role=Role.CREATOR)
        self.workspace1 = Workspace.objects.create(name="Creator 1 WS", owner=self.creator1, slug="growth-c1-ws")
        CreatorProfile.objects.create(user=self.creator1, niche="Tech & AI")

        # Creator 2 (for multi-tenant isolation testing)
        self.creator2 = User.objects.create_user(username='growth_creator_2', password='password123', role=Role.CREATOR)
        self.workspace2 = Workspace.objects.create(name="Creator 2 WS", owner=self.creator2, slug="growth-c2-ws")
        CreatorProfile.objects.create(user=self.creator2, niche="Fitness")

    # ----------------------------------------------------
    # 1. Voice Profile Tests
    # ----------------------------------------------------
    def test_voice_profile_creation_and_editing(self):
        self.client.login(username='growth_creator_1', password='password123')
        
        # Initial view auto-creates default profile
        response = self.client.get(reverse('creator_voice_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CreatorVoiceProfile.objects.filter(creator=self.creator1).exists())

        profile = CreatorVoiceProfile.objects.get(creator=self.creator1)
        self.assertEqual(profile.workspace, self.workspace1)

        # Edit profile POST
        edit_response = self.client.post(reverse('creator_voice_profile'), {
            'action': 'update_profile',
            'name': 'Alex High Voltage Tech',
            'niche': 'AI Engineering',
            'sub_niche': 'Agentic Workflows',
            'target_audience': 'Senior Developers & CTOs',
            'preferred_language': 'HINGLISH',
            'tone_of_voice': 'Ultra Direct & Punchy',
            'preferred_hook_style': 'Contrarian Question',
            'typical_script_length': '30-45s',
            'common_content_themes': 'LLM deployment, prompt security',
            'preferred_cta_style': "Comment 'CODE' for the GitHub repo",
            'words_to_use': 'listen up, no BS, ship faster',
            'words_to_avoid': 'delve, tapestry, in conclusion',
            'is_active': 'on'
        })
        self.assertRedirects(edit_response, reverse('creator_voice_profile'))

        profile.refresh_from_db()
        self.assertEqual(profile.name, 'Alex High Voltage Tech')
        self.assertEqual(profile.tone_of_voice, 'Ultra Direct & Punchy')
        self.assertEqual(profile.preferred_language, 'HINGLISH')
        self.assertTrue(profile.is_active)

    def test_voice_sample_lifecycle_and_synthesis(self):
        self.client.login(username='growth_creator_1', password='password123')
        profile = CreatorVoiceProfile.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            name="Sample Voice Profile"
        )

        # Add Sample
        add_resp = self.client.post(reverse('creator_voice_sample_add'), {
            'title': 'Viral Python Script',
            'sample_type': 'REEL_SCRIPT',
            'content': 'Listen up. 99% of people are writing slow loops. Use vectorization instead.',
            'performance_notes': '150k views on Instagram'
        })
        self.assertRedirects(add_resp, reverse('creator_voice_profile'))
        self.assertEqual(profile.samples.count(), 1)

        # Trigger AI Style Synthesis
        synth_resp = self.client.post(reverse('creator_voice_synthesize'))
        self.assertRedirects(synth_resp, reverse('creator_voice_profile'))
        
        profile.refresh_from_db()
        self.assertTrue(len(profile.ai_style_summary) > 20)
        self.assertIn("Creator Voice Blueprint", profile.ai_style_summary)

        # Delete Sample
        sample = profile.samples.first()
        del_resp = self.client.post(reverse('creator_voice_sample_delete', kwargs={'sample_id': sample.id}))
        self.assertRedirects(del_resp, reverse('creator_voice_profile'))
        self.assertEqual(profile.samples.count(), 0)

    # ----------------------------------------------------
    # 2. AI Script Studio Tests
    # ----------------------------------------------------
    def test_script_generation_via_api(self):
        self.client.login(username='growth_creator_1', password='password123')

        # Test AJAX script generation endpoint
        response = self.client.post(reverse('creator_script_generate_api'), {
            'topic': '3 Free AI Tools to Automate Cold Outreach',
            'niche': 'Tech & AI',
            'sub_niche': 'B2B Sales',
            'target_audience': 'Founders & Sales Reps',
            'language': 'ENGLISH',
            'duration': '30-60s',
            'objective': 'LEADS',
            'apply_voice_profile': 'true'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('script_id', data)
        self.assertEqual(len(data['script']['hooks']), 5)
        self.assertTrue(len(data['script']['script_body']) > 50)
        self.assertTrue(len(data['script']['scenes']) >= 2)

        # Check real database persistence
        script = AIScript.objects.get(id=data['script_id'])
        self.assertEqual(script.creator, self.creator1)
        self.assertEqual(script.workspace, self.workspace1)
        self.assertEqual(script.objective, 'LEADS')
        self.assertEqual(script.version_number, 1)

    def test_hook_regeneration_api(self):
        self.client.login(username='growth_creator_1', password='password123')
        response = self.client.post(reverse('creator_script_regenerate_hooks_api'), {
            'topic': 'Automating Instagram DMs',
            'niche': 'Tech & AI',
            'objective': 'GROWTH',
            'language': 'ENGLISH'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['hooks']), 5)

    def test_script_versioning(self):
        self.client.login(username='growth_creator_1', password='password123')
        script = AIScript.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Initial Outreach Script",
            topic="Outreach",
            script_body="Original talking points.",
            hooks=["Hook 1", "Hook 2"],
            version_number=1
        )

        # Snapshot new version
        response = self.client.post(reverse('creator_script_create_version', kwargs={'script_id': script.id}), {
            'change_summary': 'Added stronger call to action'
        })
        self.assertEqual(response.status_code, 302)

        script.refresh_from_db()
        self.assertEqual(script.version_number, 2)
        self.assertEqual(script.versions.count(), 1)
        self.assertEqual(script.versions.first().change_summary, 'Added stronger call to action')

    def test_script_ownership_and_tenant_isolation(self):
        # Script owned by Creator 1
        script1 = AIScript.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Creator 1 Private Script",
            topic="Private Secrets",
            script_body="Confidential text"
        )

        # Creator 2 attempts to view Creator 1's script -> MUST be 404
        self.client.login(username='growth_creator_2', password='password123')
        detail_resp = self.client.get(reverse('creator_script_detail', kwargs={'script_id': script1.id}))
        self.assertEqual(detail_resp.status_code, 404)

        # Creator 2 attempts to delete Creator 1's script -> MUST be 404
        del_resp = self.client.post(reverse('creator_script_delete', kwargs={'script_id': script1.id}))
        self.assertEqual(del_resp.status_code, 404)
        self.assertTrue(AIScript.objects.filter(id=script1.id).exists())

    # ----------------------------------------------------
    # 3. Viral Finder & Breakout Scoring Tests
    # ----------------------------------------------------
    def test_breakout_scoring_with_creator_baseline(self):
        # 5x baseline -> Mega Viral (98.0)
        res_5x = BreakoutScoringEngine.calculate_score(views_count=500000, likes_count=35000, comments_count=1200, creator_avg_views=100000)
        self.assertEqual(res_5x['breakout_score'], Decimal('98.0'))
        self.assertEqual(res_5x['breakout_ratio'], Decimal('5.00'))
        self.assertTrue(res_5x['has_historical_baseline'])
        self.assertIn("Mega Viral", res_5x['breakout_label'])

        # 3.2x baseline -> High Breakout (91.5)
        res_3x = BreakoutScoringEngine.calculate_score(views_count=320000, likes_count=22000, comments_count=800, creator_avg_views=100000)
        self.assertEqual(res_3x['breakout_score'], Decimal('91.5'))
        self.assertEqual(res_3x['breakout_ratio'], Decimal('3.20'))

        # Normal views (0.9x) -> Typical Performance (55.0)
        res_norm = BreakoutScoringEngine.calculate_score(views_count=90000, likes_count=5000, comments_count=150, creator_avg_views=100000)
        self.assertEqual(res_norm['breakout_score'], Decimal('55.0'))
        self.assertIn("Typical", res_norm['breakout_label'])

    def test_breakout_scoring_without_baseline_estimate(self):
        # High engagement rate without creator baseline
        res_est = BreakoutScoringEngine.calculate_score(views_count=100000, likes_count=11000, comments_count=1500, creator_avg_views=0)
        self.assertEqual(res_est['breakout_score'], Decimal('85.0'))
        self.assertFalse(res_est['has_historical_baseline'])
        self.assertIn("Estimated", res_est['breakout_label'])

    def test_manual_video_import_and_analysis_workflow(self):
        self.client.login(username='growth_creator_1', password='password123')

        # Import a reference video
        import_resp = self.client.post(reverse('creator_viral_import'), {
            'video_url': 'https://www.instagram.com/reel/C3_test_reel/',
            'creator_name': 'Alex Creator',
            'creator_handle': '@alexcreator',
            'caption': 'Stop doing automation wrong. Use this 3-step loop.',
            'niche': 'Tech & AI',
            'views_count': 350000,
            'likes_count': 25000,
            'comments_count': 850,
            'creator_avg_views': 80000
        })
        self.assertEqual(import_resp.status_code, 302)

        video = DiscoveredVideo.objects.get(workspace=self.workspace1)
        self.assertEqual(video.creator_handle, 'alexcreator')
        self.assertEqual(video.breakout_ratio, Decimal('4.38'))
        self.assertEqual(video.breakout_score, Decimal('91.5'))

        # Deep AI Analysis
        analyze_resp = self.client.get(reverse('creator_viral_analyze', kwargs={'video_id': video.id}))
        self.assertEqual(analyze_resp.status_code, 200)
        self.assertTrue(VideoAnalysis.objects.filter(video=video).exists())
        analysis = VideoAnalysis.objects.get(video=video)
        self.assertTrue(len(analysis.hook_breakdown) > 10)
        self.assertTrue(len(analysis.retention_triggers) >= 2)

        # Bookmark to Inspiration
        save_resp = self.client.post(reverse('creator_viral_save_inspiration', kwargs={'video_id': video.id}))
        self.assertTrue(SavedInspiration.objects.filter(creator=self.creator1, video=video).exists())

    def test_all_growth_studio_pages_render_200(self):
        self.client.login(username='growth_creator_1', password='password123')
        endpoints = [
            'creator_growth_studio_overview',
            'creator_script_studio',
            'creator_viral_finder',
            'creator_voice_profile',
        ]
        for ep in endpoints:
            res = self.client.get(reverse(ep))
            self.assertEqual(res.status_code, 200, f"Page {ep} failed with {res.status_code}")

    # ----------------------------------------------------
    # 4. Mocked External LLM Provider Test
    # ----------------------------------------------------
    @patch('creator.services.ai_growth_service.AIGrowthService.get_configured_provider')
    def test_mocked_llm_response_parsing(self, mock_get_provider):
        mock_get_provider.return_value = ('OPENAI', 'sk-test-mock-key')

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "title": "Mocked AI Reel",
                "hooks": ["Hook A", "Hook B", "Hook C", "Hook D", "Hook E"],
                "selected_hook": "Hook A",
                "script_body": "This is a mocked LLM script body with deep viral structure.",
                "scenes": [{"scene_number": 1, "timestamp": "0:00 - 0:03", "visual": "Fast zoom", "audio": "Hook A", "on_screen_text": "STOP"}],
                "on_screen_text": "STOP NOW",
                "caption": "Great video caption #viral",
                "hashtags": "#viral #reels",
                "cta": "Comment 'AI' for link",
                "filming_tips": "Film in 9:16 vertical"
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_completion

        with patch.dict('sys.modules', {'openai': mock_openai}):
            res = AIGrowthService.generate_reel_script(topic="Mock Topic", language="ENGLISH")
            self.assertEqual(res['title'], 'Mocked AI Reel')
            self.assertEqual(len(res['hooks']), 5)
            self.assertEqual(res['selected_hook'], 'Hook A')
            self.assertIn("mocked LLM script body", res['script_body'])

    # ----------------------------------------------------
    # 5. Gemini Optimization & Token Safeguard Tests
    # ----------------------------------------------------
    def test_ai_token_usage_cost_calculation(self):
        """
        Tests calculation of estimated USD cost based on token counts and model pricing.
        """
        # 10,000 prompt tokens ($0.075/1M) + 5,000 completion tokens ($0.300/1M)
        cost = AITokenUsage.calculate_cost(prompt_tokens=10000, completion_tokens=5000)
        expected_cost = Decimal('10000') / Decimal('1000000') * Decimal('0.075') + Decimal('5000') / Decimal('1000000') * Decimal('0.300')
        self.assertEqual(cost, round(expected_cost, 8))

    def test_ai_token_usage_record_and_get_user_stats(self):
        """
        Tests recording usage entries and aggregating 24h user metrics (tokens, cost, cache hit rate).
        """
        # Record 1: Normal API call
        AITokenUsage.record(
            workspace=self.workspace1,
            user=self.creator1,
            feature="TRENDING_REEL",
            model_name="gemini-3.8-flash",
            prompt_tokens=500,
            completion_tokens=200,
            was_cached=False,
            status="SUCCESS"
        )

        # Record 2: Cached call (0 tokens, 0 cost)
        AITokenUsage.record(
            workspace=self.workspace1,
            user=self.creator1,
            feature="NICHE_RELEVANCE",
            model_name="cache-hit",
            prompt_tokens=0,
            completion_tokens=0,
            was_cached=True,
            status="CACHED"
        )

        stats = AITokenUsage.get_user_stats(self.creator1, hours=24)
        self.assertEqual(stats['total_requests'], 2)
        self.assertEqual(stats['cached_requests'], 1)
        self.assertEqual(stats['api_requests'], 1)
        self.assertEqual(stats['total_tokens'], 700)
        self.assertEqual(stats['cache_hit_rate_pct'], 50.0)
        self.assertGreater(stats['total_cost_usd'], 0.0)

    def test_ai_token_usage_quota_safeguard(self):
        """
        Tests per-user safeguard throttling when hourly request limits are exceeded.
        """
        allowed, reason, retry_after = AITokenUsage.check_user_quota(self.creator1)
        self.assertTrue(allowed)

        # Simulate reaching hourly max
        for _ in range(30):
            AITokenUsage.objects.create(
                workspace=self.workspace1,
                user=self.creator1,
                feature="NICHE_RELEVANCE",
                model_name="gemini-3.8-flash",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=Decimal('0.00001'),
                was_cached=False,
                status="SUCCESS"
            )

        allowed_after, reason_after, retry_after_sec = AITokenUsage.check_user_quota(self.creator1)
        self.assertFalse(allowed_after)
        self.assertIn("Hourly AI generation limit", reason_after)
        self.assertGreater(retry_after_sec, 0)

    @patch('creator.services.ai_growth_service.AIGrowthService._get_gemini_model')
    def test_ai_growth_service_cache_hit_and_zero_tokens(self, mock_get_model):
        """
        Verifies that repeated queries to generate_content_ideas hit cache,
        returning reusable results while consuming 0 additional API tokens.
        """
        mock_model = MagicMock()
        mock_model.model_name = "gemini-3.8-flash"
        mock_resp = MagicMock()
        mock_resp.text = json.dumps([
            {"topic": "5 AI Tools in 2026", "hook_angle": "Productivity", "format_suggestion": "Screen record"},
            {"topic": "Automate your workflow", "hook_angle": "Time saving", "format_suggestion": "Talking head"}
        ])
        mock_resp.usage_metadata = MagicMock()
        mock_resp.usage_metadata.prompt_token_count = 120
        mock_resp.usage_metadata.candidates_token_count = 80
        mock_model.generate_content.return_value = mock_resp

        mock_genai = MagicMock()
        mock_get_model.return_value = (mock_model, mock_genai)

        # Call 1 (populates cache)
        res1 = AIGrowthService.generate_content_ideas(
            niche="Technology",
            count=2,
            workspace=self.workspace1,
            user=self.creator1
        )
        self.assertIsInstance(res1, list)
        self.assertEqual(len(res1), 2)

        # Call 2 (must hit cache: 0 additional API calls, 0 tokens)
        res2 = AIGrowthService.generate_content_ideas(
            niche="Technology",
            count=2,
            workspace=self.workspace1,
            user=self.creator1
        )
        self.assertEqual(res1, res2)

        # Gemini model should have only been invoked once
        mock_model.generate_content.assert_called_once()

        # Verify a cached record was logged
        cached_record = AITokenUsage.objects.filter(
            user=self.creator1,
            was_cached=True,
            status='CACHED'
        ).last()
        self.assertIsNotNone(cached_record)
        self.assertEqual(cached_record.total_tokens, 0)
        self.assertEqual(cached_record.estimated_cost_usd, Decimal('0.00000000'))

    def test_growth_studio_overview_displays_ai_usage_stats(self):
        """
        Tests that Creator Growth Studio Overview displays AI token metrics and optimization badge.
        """
        AITokenUsage.record(
            workspace=self.workspace1,
            user=self.creator1,
            feature="TEST_FEATURE",
            model_name="gemini-3.8-flash",
            prompt_tokens=400,
            completion_tokens=150,
            was_cached=False,
            status="SUCCESS"
        )

        self.client.login(username='growth_creator_1', password='password123')
        resp = self.client.get(reverse('creator_growth_studio_overview'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ai_usage_stats', resp.context)
        self.assertEqual(resp.context['ai_usage_stats']['total_requests'], 1)
        self.assertEqual(resp.context['ai_usage_stats']['total_tokens'], 550)
        self.assertContains(resp, "AI Engine Optimization & Safeguards")
        self.assertContains(resp, "Tokens Used")

    # ----------------------------------------------------
    # 7. Content Idea Generator Tests
    # ----------------------------------------------------
    def test_content_ideas_view_and_filtering(self):
        self.client.login(username='growth_creator_1', password='password123')
        
        # Create ideas
        idea1 = ContentIdea.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="5 Python Automation Scripts for 2026",
            hook="Stop doing manual work.",
            content_angle="Direct productivity boost",
            niche="Tech & AI",
            language="ENGLISH",
            objective="GROWTH",
            is_favorite=True
        )
        idea2 = ContentIdea.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Kaise kare AI tool setup",
            hook="Agar aap student ho toh ye dekho.",
            content_angle="Student discount trick",
            niche="Tech & AI",
            language="HINGLISH",
            objective="EDUCATE"
        )

        resp = self.client.get(reverse('creator_content_ideas'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "5 Python Automation Scripts")
        self.assertContains(resp, "Kaise kare AI tool setup")

        # Filter by language
        resp_lang = self.client.get(reverse('creator_content_ideas') + '?language=HINGLISH')
        self.assertEqual(resp_lang.status_code, 200)
        self.assertContains(resp_lang, "Kaise kare AI tool setup")
        self.assertNotContains(resp_lang, "5 Python Automation Scripts")

        # Filter by favorite
        resp_fav = self.client.get(reverse('creator_content_ideas') + '?favorite=1')
        self.assertEqual(resp_fav.status_code, 200)
        self.assertContains(resp_fav, "5 Python Automation Scripts")
        self.assertNotContains(resp_fav, "Kaise kare AI tool setup")

    def test_content_ideas_batch_generate_api(self):
        self.client.login(username='growth_creator_1', password='password123')
        
        resp = self.client.post(reverse('creator_content_ideas_batch_generate_api'), {
            'niche': 'Tech & AI',
            'sub_niche': 'Developer Tools',
            'target_audience': 'Software Engineers',
            'language': 'ENGLISH',
            'objective': 'GROWTH',
            'count': 3,
            'use_voice_profile': 'true',
            'use_context': 'true'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIsInstance(data.get('ideas'), list)
        self.assertGreaterEqual(len(data['ideas']), 2)
        first_idea = data['ideas'][0]
        self.assertIn('title', first_idea)
        self.assertIn('hook', first_idea)
        self.assertIn('content_angle', first_idea)

    def test_content_idea_crud_and_isolation(self):
        self.client.login(username='growth_creator_1', password='password123')
        
        # 1. Save Idea
        save_resp = self.client.post(
            reverse('creator_content_idea_save_api'),
            json.dumps({
                'title': 'AI Workflow Architecture',
                'hook': 'This 1 diagram replaced 3 tools',
                'content_angle': 'Architecture simplicity',
                'suggested_format': 'Screen Demo',
                'niche': 'Tech & AI',
                'language': 'ENGLISH',
                'objective': 'GROWTH'
            }),
            content_type='application/json'
        )
        self.assertEqual(save_resp.status_code, 200)
        data = save_resp.json()
        self.assertEqual(data['status'], 'success')
        idea_id = data['idea_id']

        idea = ContentIdea.objects.get(id=idea_id)
        self.assertEqual(idea.creator, self.creator1)
        self.assertEqual(idea.workspace, self.workspace1)

        # 2. Toggle Favorite
        fav_resp = self.client.post(reverse('creator_content_idea_toggle_favorite_api', kwargs={'idea_id': idea.id}))
        self.assertEqual(fav_resp.status_code, 200)
        idea.refresh_from_db()
        self.assertTrue(idea.is_favorite)

        # 3. Edit Idea
        edit_resp = self.client.post(
            reverse('creator_content_idea_edit_api', kwargs={'idea_id': idea.id}),
            json.dumps({'title': 'Updated AI Workflow Architecture'}),
            content_type='application/json'
        )
        self.assertEqual(edit_resp.status_code, 200)
        idea.refresh_from_db()
        self.assertEqual(idea.title, 'Updated AI Workflow Architecture')

        # 4. Multi-Tenant Isolation: Creator 2 cannot delete or edit Creator 1's idea
        self.client.login(username='growth_creator_2', password='password123')
        del_attempt = self.client.post(reverse('creator_content_idea_delete_api', kwargs={'idea_id': idea.id}))
        self.assertEqual(del_attempt.status_code, 404)
        self.assertTrue(ContentIdea.objects.filter(id=idea.id).exists())

        # Creator 1 deletes successfully
        self.client.login(username='growth_creator_1', password='password123')
        del_success = self.client.post(reverse('creator_content_idea_delete_api', kwargs={'idea_id': idea.id}))
        self.assertEqual(del_success.status_code, 302)
        self.assertFalse(ContentIdea.objects.filter(id=idea.id).exists())

    # ----------------------------------------------------
    # 8. Content Calendar Tests
    # ----------------------------------------------------
    def test_content_calendar_view_and_pipeline_counts(self):
        self.client.login(username='growth_creator_1', password='password123')

        # Create calendar entries with distinct statuses
        ContentCalendarEntry.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Entry Idea 1",
            scheduled_date="2026-10-20",
            status="IDEA"
        )
        ContentCalendarEntry.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Entry Film Ready",
            scheduled_date="2026-10-21",
            status="READY_TO_FILM"
        )
        ContentCalendarEntry.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Entry Published",
            scheduled_date="2026-10-22",
            status="PUBLISHED"
        )

        resp = self.client.get(reverse('creator_content_calendar') + '?view=list')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Entry Idea 1")
        self.assertContains(resp, "Entry Film Ready")
        self.assertContains(resp, "Entry Published")

        status_counts = resp.context['status_counts']
        self.assertEqual(status_counts['ALL'], 3)
        self.assertEqual(status_counts['IDEA'], 1)
        self.assertEqual(status_counts['READY_TO_FILM'], 1)
        self.assertEqual(status_counts['PUBLISHED'], 1)

    def test_content_calendar_entry_crud_and_reschedule(self):
        self.client.login(username='growth_creator_1', password='password123')

        # Create entry via API
        create_resp = self.client.post(
            reverse('creator_calendar_entry_create_api'),
            json.dumps({
                'title': 'How to Build an AI Agent',
                'scheduled_date': '2026-10-25',
                'scheduled_time': '14:30',
                'status': 'SCRIPT_READY',
                'content_type': 'REEL',
                'category': 'Tutorial',
                'notes': 'Use split screen'
            }),
            content_type='application/json'
        )
        self.assertEqual(create_resp.status_code, 200)
        data = create_resp.json()
        entry_id = data['entry_id']

        entry = ContentCalendarEntry.objects.get(id=entry_id)
        self.assertEqual(entry.creator, self.creator1)
        self.assertEqual(entry.status, 'SCRIPT_READY')
        self.assertEqual(str(entry.scheduled_date), '2026-10-25')

        # Reschedule Entry via fast API
        reschedule_resp = self.client.post(
            reverse('creator_calendar_reschedule_api', kwargs={'entry_id': entry.id}),
            json.dumps({
                'scheduled_date': '2026-10-30',
                'status': 'READY_TO_FILM'
            }),
            content_type='application/json'
        )
        self.assertEqual(reschedule_resp.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(str(entry.scheduled_date), '2026-10-30')
        self.assertEqual(entry.status, 'READY_TO_FILM')

        # Isolation test: Creator 2 cannot delete entry
        self.client.login(username='growth_creator_2', password='password123')
        del_attempt = self.client.post(reverse('creator_calendar_entry_delete_api', kwargs={'entry_id': entry.id}))
        self.assertEqual(del_attempt.status_code, 404)
        self.assertTrue(ContentCalendarEntry.objects.filter(id=entry.id).exists())

        # Creator 1 deletes successfully
        self.client.login(username='growth_creator_1', password='password123')
        del_success = self.client.post(reverse('creator_calendar_entry_delete_api', kwargs={'entry_id': entry.id}))
        self.assertEqual(del_success.status_code, 302)
        self.assertFalse(ContentCalendarEntry.objects.filter(id=entry.id).exists())

    def test_calendar_operations_do_not_call_gemini(self):
        """
        Calendar operations must strictly be pure Django & PostgreSQL operations (0 AI token cost).
        """
        self.client.login(username='growth_creator_1', password='password123')
        initial_token_records = AITokenUsage.objects.count()

        # Create
        self.client.post(
            reverse('creator_calendar_entry_create_api'),
            json.dumps({'title': 'Zero AI Test', 'scheduled_date': '2026-10-28', 'status': 'IDEA'}),
            content_type='application/json'
        )
        entry = ContentCalendarEntry.objects.get(title='Zero AI Test')

        # Reschedule
        self.client.post(
            reverse('creator_calendar_reschedule_api', kwargs={'entry_id': entry.id}),
            json.dumps({'scheduled_date': '2026-10-29'}),
            content_type='application/json'
        )

        # View Calendar
        self.client.get(reverse('creator_content_calendar'))

        final_token_records = AITokenUsage.objects.count()
        self.assertEqual(initial_token_records, final_token_records)

    # ----------------------------------------------------
    # 9. Inspiration Library Tests
    # ----------------------------------------------------
    def test_inspiration_library_view_and_filtering(self):
        self.client.login(username='growth_creator_1', password='password123')

        item1 = InspirationItem.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Viral Hook by @techguru",
            source_type="HOOK",
            hook_text="Stop paying for cloud compute.",
            category="Tech & AI",
            is_favorite=True
        )
        item2 = InspirationItem.objects.create(
            workspace=self.workspace1,
            creator=self.creator1,
            title="Fitness Reel Breakdown",
            source_type="URL",
            source_url="https://instagram.com/reel/xyz123",
            category="Fitness",
            is_favorite=False
        )

        resp = self.client.get(reverse('creator_inspiration_library'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Viral Hook by @techguru")
        self.assertContains(resp, "Fitness Reel Breakdown")

        # Search
        resp_search = self.client.get(reverse('creator_inspiration_library') + '?q=cloud+compute')
        self.assertContains(resp_search, "Viral Hook by @techguru")
        self.assertNotContains(resp_search, "Fitness Reel Breakdown")

        # Filter by source_type
        resp_type = self.client.get(reverse('creator_inspiration_library') + '?source_type=HOOK')
        self.assertContains(resp_type, "Viral Hook by @techguru")
        self.assertNotContains(resp_type, "Fitness Reel Breakdown")

    def test_inspiration_library_add_and_url_validation(self):
        self.client.login(username='growth_creator_1', password='password123')

        # Invalid URL fails validation
        bad_resp = self.client.post(
            reverse('creator_inspiration_add_api'),
            json.dumps({'title': 'Bad URL Item', 'source_url': 'not_a_valid_url'}),
            content_type='application/json'
        )
        self.assertEqual(bad_resp.status_code, 400)
        self.assertIn('valid URL', bad_resp.json()['message'])

        # Valid item succeeds
        good_resp = self.client.post(
            reverse('creator_inspiration_add_api'),
            json.dumps({
                'title': 'Masterclass Opening Hook',
                'source_type': 'HOOK',
                'hook_text': 'I tested 50 AI models so you do not have to.',
                'category': 'Tech & AI'
            }),
            content_type='application/json'
        )
        self.assertEqual(good_resp.status_code, 200)
        self.assertEqual(good_resp.json()['status'], 'success')
        item_id = good_resp.json()['item_id']

        item = InspirationItem.objects.get(id=item_id)
        self.assertEqual(item.creator, self.creator1)

        # Toggle favorite
        fav_resp = self.client.post(reverse('creator_inspiration_toggle_favorite_api', kwargs={'item_id': item.id}))
        self.assertEqual(fav_resp.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_favorite)

        # Creator 2 cannot delete Creator 1's item
        self.client.login(username='growth_creator_2', password='password123')
        del_attempt = self.client.post(reverse('creator_inspiration_delete_api', kwargs={'item_id': item.id}))
        self.assertEqual(del_attempt.status_code, 404)
        self.assertTrue(InspirationItem.objects.filter(id=item.id).exists())

    # ----------------------------------------------------
    # 10. Performance Coach Tests
    # ----------------------------------------------------
    def test_performance_coach_view_disconnected(self):
        """
        When Instagram account is not connected, displays clear instructions without error.
        """
        self.client.login(username='growth_creator_1', password='password123')
        resp = self.client.get(reverse('creator_performance_coach'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Instagram Account Not Connected")
        self.assertContains(resp, "Connect Instagram Now")
        self.assertFalse(resp.context['perf_data']['connected'])

    def test_performance_coach_view_connected_no_posts(self):
        """
        When connected account exists but has no posts or token, handles gracefully.
        """
        self.client.login(username='growth_creator_1', password='password123')
        
        # Connect Social Account
        SocialAccount.objects.create(
            workspace=self.workspace1,
            platform='INSTAGRAM',
            account_id='ig_test_123',
            account_name='Test Account',
            username='test_creator_ig',
            is_connected=True
        )

        resp = self.client.get(reverse('creator_performance_coach'))
        self.assertEqual(resp.status_code, 200)
        # Should explain that token is missing or reconnection needed
        self.assertContains(resp, "Social Accounts")

    @patch.object(PerformanceCoachService, 'get_account_performance')
    def test_performance_coach_on_demand_ai_analysis(self, mock_get_perf):
        """
        Explicit AI Coach recommendation trigger:
        Evaluates observed metrics and stores report, separating observed data from hypotheses.
        """
        self.client.login(username='growth_creator_1', password='password123')

        mock_get_perf.return_value = {
            'connected': True,
            'account': None,
            'status': 'ACTIVE',
            'post_count': 10,
            'total_reach': 120000,
            'total_likes': 4500,
            'total_comments': 620,
            'total_saves': 248,
            'total_shares': 675,
            'avg_engagement_rate': 4.27,
            'top_posts': [
                {'caption': 'Top Reel on Prompt Security', 'likes': 2100, 'comments': 310, 'media_type': 'REEL'}
            ],
            'message': 'Observed 10 posts'
        }

        # Explicit trigger
        resp = self.client.post(
            reverse('creator_performance_coach_ai_analyze_api'),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('report', data)
        self.assertTrue(len(data['report']['summary']) > 10)
        self.assertIsInstance(data['report']['strengths'], list)
        self.assertIsInstance(data['report']['recommended_experiments'], list)

        # Verify persisted in database
        report = PerformanceCoachReport.objects.filter(workspace=self.workspace1, creator=self.creator1).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.observed_metrics['total_reach'], 120000)
        self.assertEqual(report.observed_metrics['avg_engagement_rate'], 4.27)


