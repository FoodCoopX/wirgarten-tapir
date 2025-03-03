from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from tapir.jokers.serializers import JokerSerializer, GetJokersRequestSerializer


class GetJokers(APIView):
    @extend_schema(
        responses={200: JokerSerializer(many=True)},
        request=GetJokersRequestSerializer,
    )
    def post(self, request):
        request_serializer = SendAnswerGermanWordSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        answer = request_serializer.validated_data["answer"]
        word = get_object_or_404(Word, id=request_serializer.validated_data["word_id"])
        GermanWordResult.objects.create(answer=answer, word=word, user=request.user)

        learned = False
        if WordLearnedChecker.is_word_learned(request.user, word):
            learned = True
            LearnedWord.objects.create(user=request.user, word=word)

        return Response(
            WasAnswerCorrectSerializer(
                {
                    "correct": answer == word.gender,
                    "learned": learned,
                    "nb_answers_correct_in_a_row": WordLearnedChecker.nb_correct_in_a_row(
                        request.user, word
                    ),
                    "repetitions_to_learn": LearningConfig.REPETITIONS_TO_LEARN,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
