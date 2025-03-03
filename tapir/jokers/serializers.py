from rest_framework import serializers

from tapir.jokers.models import Joker


class JokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Joker
        fields = "__all__"


class GetJokersRequestSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
