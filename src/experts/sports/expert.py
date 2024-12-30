"""Sports expert implementation"""
from typing import Dict, List, Optional, Any
import logging
from src.core.base_expert import BaseExpert
from src.utils.openai_client import OpenAIClient
from src.utils.web_search import WebSearchClient
from src.utils.cache import Cache
from .sources.local_data import get_knowledge_base, get_common_questions, find_answer
from .sources.url_sources import get_url_sources, search_url_sources
import json

class SportsExpert(BaseExpert):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("sports")
        self.config = config
        self.openai_client = OpenAIClient()
        self.web_search = WebSearchClient()
        self.cache = Cache(
            enabled=config["experts"]["sports"]["cache_enabled"],
            ttl=config["experts"]["sports"]["cache_ttl"]
        )
        self.logger = logging.getLogger(__name__)
        
    async def get_response(self, query: str) -> Optional[str]:
        """Main response generation pipeline"""
        try:
            # Check cache first
            cached_response = self.cache.get(query)
            if cached_response:
                return cached_response
                
            # Step 1: Check local knowledge base
            local_response = await self._check_local_knowledge(query)
            if local_response:
                self.cache.set(query, local_response)
                return local_response
                
            # Step 2: Check URL sources
            url_response = await self._check_url_sources(query)
            if url_response:
                self.cache.set(query, url_response)
                return url_response
                
            # Step 3: Generate response using OpenAI
            ai_response = await self._generate_ai_response(query)
            if ai_response:
                self.cache.set(query, ai_response)
                return ai_response
                
            # Step 4: Web search as last resort
            web_response = await self._perform_web_search(query)
            if web_response:
                self.cache.set(query, web_response)
                return web_response
                
            # Step 5: Fallback response
            return "I apologize, but I couldn't find a satisfactory answer to your sports-related question. Could you please rephrase or provide more details?"
            
        except Exception as e:
            self.logger.error(f"Error in get_response: {str(e)}")
            return "I encountered an error while processing your sports-related request. Please try again."
            
    async def _check_local_knowledge(self, query: str) -> Optional[str]:
        """Check local knowledge base for relevant information"""
        try:
            kb = get_knowledge_base()
            return find_answer(query)
        except Exception as e:
            self.logger.error(f"Error checking local knowledge: {str(e)}")
            return None
        
    async def _check_url_sources(self, query: str) -> Optional[str]:
        """Check URL sources for relevant information"""
        try:
            return await search_url_sources(query)
        except Exception as e:
            self.logger.error(f"Error checking URL sources: {str(e)}")
            return None
        
    async def _generate_ai_response(self, query: str) -> Optional[str]:
        """Generate response using OpenAI"""
        system_prompt = """You are a sports expert assistant. Provide accurate and helpful responses
        about sports, athletes, teams, competitions, rules, and sports history. If you're not confident
        about the answer, indicate that."""
        
        try:
            response = await self.openai_client.get_completion(system_prompt, query)
            return response
        except Exception as e:
            self.logger.error(f"Error generating AI response: {str(e)}")
            return None
            
    async def _perform_web_search(self, query: str) -> Optional[str]:
        """Perform web search and generate response based on results"""
        try:
            # Add sports context to search query
            search_query = f"{query} spor haberleri güncel"
            search_results = await self.web_search.search(search_query)
            
            if not search_results:
                return None
                
            # Generate response based on search results
            context = "\n".join(search_results[:3])  # Use top 3 results
            system_prompt = """Sen bir spor uzmanısın. Web arama sonuçlarını kullanarak soruya kapsamlı ve doğru bir yanıt üretmelisin.
            Yanıt üretirken şu kurallara uy:
            1. Web arama sonuçlarındaki bilgilerin doğruluğunu kontrol et
            2. Bilgilerin güncelliğini kontrol et
            3. Çelişkili bilgiler varsa en güvenilir kaynağı seç
            4. Emin olmadığın bilgileri verme
            5. Yanıtı net ve anlaşılır bir şekilde ver"""
            
            response = await self.openai_client.get_completion(
                system_prompt,
                f"Soru: {query}\n\nWeb arama sonuçları:\n{context}\n\nBu bilgileri kullanarak soruya yanıt ver."
            )
            
            if response:
                # Validate response with another OpenAI call
                validation_prompt = """Web arama sonuçlarından üretilen yanıtın doğruluğunu kontrol et.
                Yanıt güvenilir ve güncel bilgiler içeriyorsa onay ver.
                Yanıt JSON formatında olmalı: {"is_valid": boolean, "reason": string}"""
                
                validation = await self.openai_client.get_completion(
                    validation_prompt,
                    f"Yanıt: {response}\n\nKaynaklar:\n{context}"
                )
                
                try:
                    validation_result = json.loads(validation)
                    if validation_result.get("is_valid", False):
                        return response
                except:
                    pass
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error in web search: {str(e)}")
            return None 