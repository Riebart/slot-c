myApp.controller('talkersPanelCtrl', ['$scope', '$rootScope', '$resource', '$timeout', function ($scope, $rootScope, $resource, $timeout) {

    $rootScope.backoff_factor = 1.0;

    $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + DEFAULT_CHANNEL_NAME);

    $scope.PopulateTalkers = function (Talkers) {
        if ($rootScope.chatting) {
            console.log('Retrieving Talkers from Server');
            Talkers.get(null, function (talkers) {
                console.log(talkers.participants);
                if ($rootScope.chatting) {
                    if ((typeof talkers.participants !== 'undefined') &&
                        (talkers.participants.constructor === Array) &&
                        (talkers.participants.length > 0)) {
                        var myUserName = $rootScope.userName;
                        $scope.talkers = talkers.participants.filter(function (v) {
                            return v != myUserName;
                        });
                    }
                    else {
                        $scope.talkers = talkers.participants;
                    }
                }
                else {
                    //just in case, for cleanup
                    $scope.talkers = null;
                }
            });
            return true;
        }
        else {
            return false;
        }
    }

    $rootScope.$on('channelChanged', function (event, new_channel) {
        $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + new_channel);
        $scope.PopulateTalkers($scope.TalkersResource)
    });

    $scope.TalkersRefresh = function () {
        var poll = function () {
            $timeout(function () {
                if ($scope.PopulateTalkers($scope.TalkersResource)) {
                    poll();
                }
            }, 1500 * $rootScope.backoff_factor);
        };
        poll();
    };

    $rootScope.$on("chatting", $scope.TalkersRefresh);
    $scope.$on("async_init", $scope.TalkersRefresh);

    $rootScope.$on("not chatting", function () {
        //clear our model, which will clear out the messages from the panel
        $scope.talkers = null;
    });

    if (localStorage.getItem('userName') !== null) {
        $scope.$emit('async_init');
    }

}]);
